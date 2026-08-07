import datetime
import io
import logging
import re

import fitz
from django.conf import settings
from django.contrib.sites.models import Site
from django.template import loader
from django.utils.translation import activate
from dynamic_preferences.registries import global_preferences_registry
from playwright.sync_api import sync_playwright
from pypdf import PdfReader
from pypdf import PdfWriter
from sekizai.context import SekizaiContext

from sportfac.context_processors import kepchup_context


logger = logging.getLogger(__name__)

QRBILL_MARKER_TEXT = "QRBILLPAGEMARKER"

# A4 size in CSS px, matching the 120dpi Chromium's print pipeline actually uses for
# layout here (confirmed empirically: a `width: 210mm` element measured 992px live,
# i.e. 210mm at 120dpi, not the 794px the standard 96dpi CSS reference would give).
# Playwright's default viewport (1280x720) is a different, unrelated size, so leaving
# it as-is would make Chromium lay the page out for that width instead of the printed
# page's - matching the viewport to the real page size avoids that mismatch.
PDF_VIEWPORT_WIDTH_PX = 992
PDF_VIEWPORT_HEIGHT_PX = 1403

PAGE_HEIGHT_MM = 297
QRBILL_HEIGHT_MM = 105
MM_PER_PT = 25.4 / 72

PDF_MARGIN = {"top": "0", "bottom": "0", "left": "0", "right": "0"}

QRBILL_ONLY_HTML = """<!DOCTYPE html>
<html><head><style>
  @page {{ size: 210mm 105mm; margin: 0; }}
  html, body {{ margin: 0; padding: 0; }}
  svg {{ display: block; width: 210mm; height: 105mm; }}
</style></head><body>{svg}</body></html>"""

BLANK_A4_HTML = """<!DOCTYPE html>
<html><head><style>@page { size: 210mm 297mm; margin: 0; }</style></head><body></body></html>"""


def build_context_for_bill(bill):
    """Assemble the same context BillDetailView/BillMixin build for the web page.

    generate_pdf() runs outside any HTTP request (typically from a Celery task), so
    there is no view/mixin to build this context for us - it is reassembled here by
    hand from the same pieces (see registrations/views/utils.py:BillMixin and
    registrations/views/user.py:BillDetailView).
    """
    site = Site.objects.all()[0]
    static_url = f"https://{site.domain}{settings.STATIC_URL}"

    global_preferences = global_preferences_registry.manager()
    offset_days = global_preferences["payment__DELAY_DAYS"]

    registrations = list(bill.registrations.all())
    for registration in registrations:
        registration.row_span = 1 + registration.extra_infos.count()

    context = {
        "bill": bill,
        "invoice": bill,  # invoice-part-*.html and the base billing_partial.html expect "invoice"
        "registrations": registrations,
        "rentals": bill.rentals.all(),
        "total_amount": bill.total,
        "delay": bill.created + datetime.timedelta(days=offset_days),
        "iban": global_preferences["payment__IBAN"],
        "address": global_preferences["payment__ADDRESS"],
        "place": global_preferences["payment__PLACE"],
        # The full official QR-invoice slip is rendered separately below, pinned to
        # the page bottom - billing_partial.html's own small inline QR would duplicate it.
        "display_qr_invoice": False,
        "STATIC_URL": static_url,
        "LANGUAGE_CODE": settings.LANGUAGE_CODE,
    }
    context.update(kepchup_context(None))
    context.update(SekizaiContext().dicts[1])
    return context


def build_content_for_bill(bill):
    activate(settings.LANGUAGE_CODE)
    template = loader.get_template("registrations/bill-pdf.html")
    return template.render(build_context_for_bill(bill))


def _qrbill_offset_mm(pdf_bytes):
    """How far (mm) into its own page the content-end marker sits, or None if not found.

    The marker sits in normal flow just before #qrbill (which has
    page-break-inside:avoid), so this is content's true, unbiased end position -
    not skewed by whether #qrbill itself got pushed to a fresh page.

    Not necessarily the *last* page: not being inside #qrbill, the marker can
    render on an earlier, shared page even when #qrbill itself would get pushed
    to a fresh one right after (checked page by page since it's a unique marker,
    so wherever it's found is unambiguously the right place).
    """
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for pdf_page in doc:
            matches = pdf_page.search_for(QRBILL_MARKER_TEXT)
            if matches:
                return max(rect.y0 for rect in matches) * MM_PER_PT
    return None


def _render_pdf(playwright_page, html_content):
    playwright_page.set_content(html_content, wait_until="networkidle")
    return playwright_page.pdf(print_background=True, prefer_css_page_size=True, margin=PDF_MARGIN)


def _render_qrbill_only_pdf(playwright_page, svg_markup):
    playwright_page.set_content(QRBILL_ONLY_HTML.format(svg=svg_markup), wait_until="networkidle")
    return playwright_page.pdf(print_background=True, prefer_css_page_size=True, margin=PDF_MARGIN)


def _compose_qrbill(content_pdf_bytes, qrbill_pdf_bytes, offset_mm, blank_page_pdf_bytes=None):
    """Place the QR-invoice flush against the bottom of a page.

    Composes the final PDF ourselves with pypdf rather than fighting the browser's
    print pagination for pixel/mm-perfect placement. PDF coordinates put the origin
    at the page's bottom-left, so merging the QR-invoice's own page (already exactly
    210x105mm, nothing else on it) at (0, 0) onto a target page naturally lands it
    flush at the bottom with no transform math.

    blank_page_pdf_bytes must be provided whenever the QR-invoice needs a fresh page
    of its own (i.e. `offset_mm` leaves less than QRBILL_HEIGHT_MM free).
    """
    content_reader = PdfReader(io.BytesIO(content_pdf_bytes))
    qrbill_page = PdfReader(io.BytesIO(qrbill_pdf_bytes)).pages[0]

    writer = PdfWriter()
    for existing_page in content_reader.pages:
        writer.add_page(existing_page)

    if (PAGE_HEIGHT_MM - offset_mm) < QRBILL_HEIGHT_MM:
        blank_page = PdfReader(io.BytesIO(blank_page_pdf_bytes)).pages[0]
        writer.add_page(blank_page)

    writer.pages[-1].merge_page(qrbill_page)

    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def generate_pdf(content):
    """Render `content` (HTML string) to PDF bytes, pinning any QR-invoice to the page bottom.

    Returns None on failure rather than raising, so a broken PDF generation never
    blocks the caller (e.g. sending the accountant email with no attachment).
    """
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page(viewport={"width": PDF_VIEWPORT_WIDTH_PX, "height": PDF_VIEWPORT_HEIGHT_PX})
                page.emulate_media(media="print")

                pdf_bytes = _render_pdf(page, content)

                # If there's a QR-invoice, find where content naturally ends (independent
                # of #qrbill's own page-break-inside:avoid), strip #qrbill out, and
                # re-render the content alone so it can be composed precisely below.
                offset_mm = _qrbill_offset_mm(pdf_bytes)
                if offset_mm is None:
                    return pdf_bytes

                svg_match = re.search(r"<svg[\s\S]*?</svg>", content)
                if not svg_match:
                    return pdf_bytes

                page.evaluate("var el = document.getElementById('qrbill'); if (el) { el.remove(); }")
                content_only_pdf = page.pdf(print_background=True, prefer_css_page_size=True, margin=PDF_MARGIN)
                qrbill_only_pdf = _render_qrbill_only_pdf(page, svg_match.group(0))

                blank_page_pdf = None
                if (PAGE_HEIGHT_MM - offset_mm) < QRBILL_HEIGHT_MM:
                    page.set_content(BLANK_A4_HTML, wait_until="networkidle")
                    blank_page_pdf = page.pdf(print_background=True, prefer_css_page_size=True, margin=PDF_MARGIN)

                return _compose_qrbill(content_only_pdf, qrbill_only_pdf, offset_mm, blank_page_pdf)
            finally:
                browser.close()
    except Exception:
        logger.exception("Failed to generate bill PDF")
        return None


def generate_pdf_for_bill(bill):
    content = build_content_for_bill(bill)
    return generate_pdf(content)
