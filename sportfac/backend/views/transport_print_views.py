from datetime import date

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.generic import View
from playwright.sync_api import sync_playwright

from absences.models import Absence
from registrations.models import Registration
from registrations.models import Transport

from .mixins import FullBackendMixin


ABSENCE_LABELS = {
    "absent": "Absent",
    "excused": "Excusé",
    "medical": "Certificat médical",
    "late": "Retard",
    "canceled": "Cours annulé",
}


def transport_label(transport):
    return f"Car #{transport.name.strip()}" if transport.name.strip().isdigit() else transport.name


def transport_rows(registrations, day):
    selected = [registration for registration in registrations if day in registration.course.all_dates]
    absences = {
        (absence.child_id, absence.session.course_id): ABSENCE_LABELS.get(absence.status, "")
        for absence in Absence.objects.filter(
            session__date=day,
            session__course_id__in={registration.course_id for registration in selected},
            child_id__in={registration.child_id for registration in selected},
        ).select_related("session")
    }
    children = {}
    for registration in selected:
        child = registration.child
        row = children.setdefault(
            child.pk,
            {"child": child, "groups": set(), "courses": set(), "stops": set(), "absences": set()},
        )
        row["groups"].add(registration.course.group_name)
        row["courses"].add(registration.course.number)
        row["absences"].add(absences.get((child.pk, registration.course_id), ""))
        for answer in registration.extra_infos.all():
            if answer.key.question_label.startswith("Arr"):
                row["stops"].add(answer.value)
    rows = []
    for row in children.values():
        for key in ("groups", "courses", "stops", "absences"):
            row[key] = ", ".join(sorted(value for value in row[key] if value))
        rows.append(row)
    return sorted(
        rows,
        key=lambda row: (
            (0, int(row["child"].bib_number)) if row["child"].bib_number.isdigit() else (1, row["child"].bib_number),
            row["child"].last_name,
            row["child"].first_name,
        ),
    )


def render_transport_pdf(context):
    content = render_to_string("backend/registration/transport-paper-pdf.html", context)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            page.emulate_media(media="print")
            page.set_content(content, wait_until="networkidle")
            return page.pdf(print_background=True, prefer_css_page_size=True)
        finally:
            browser.close()


class TransportPrintView(FullBackendMixin, View):
    def get(self, request, pk):
        transport = get_object_or_404(Transport, pk=pk)
        registrations = list(
            transport.participants.select_related("child__family", "course").prefetch_related(
                "course__sessions", "extra_infos__key"
            )
        )
        dates = sorted({day for registration in registrations for day in registration.course.all_dates})
        selected_date = next((day for day in dates if day >= timezone.localdate()), None)
        error = ""
        if request.GET.get("date"):
            try:
                selected_date = date.fromisoformat(request.GET["date"])
            except ValueError:
                selected_date = None
                error = "Indiquez une date au format AAAA-MM-JJ."
            else:
                if selected_date not in dates:
                    error = "Aucun élève de ce transport n’a cours à cette date."
        rows = transport_rows(registrations, selected_date) if selected_date and not error else []
        context = {
            "transport": transport,
            "transport_label": transport_label(transport),
            "available_dates": dates,
            "selected_date": selected_date,
            "rows": rows,
            "count": len(rows),
            "error": error,
        }
        if request.GET.get("download") == "1" and rows and not error:
            response = HttpResponse(render_transport_pdf(context), content_type="application/pdf")
            response[
                "Content-Disposition"
            ] = f'attachment; filename="car-{transport.pk}-{selected_date.isoformat()}.pdf"'
            return response
        return render(
            request, "backend/registration/transport-paper-prepare.html", context, status=400 if error else 200
        )


class TransportsPrintView(FullBackendMixin, View):
    def get(self, request):
        ids = [int(value) for value in request.GET.getlist("t") if value.isdigit()]
        transports = list(Transport.objects.filter(pk__in=ids).order_by("name", "pk"))
        registrations = {transport.pk: [] for transport in transports}
        for registration in (
            Registration.objects.filter(transport__in=transports)
            .select_related("child__family", "course")
            .prefetch_related("course__sessions", "extra_infos__key")
        ):
            registrations[registration.transport_id].append(registration)
        dates = sorted(
            {day for entries in registrations.values() for entry in entries for day in entry.course.all_dates}
        )
        selected_date = next((day for day in dates if day >= timezone.localdate()), None)
        error = ""
        if request.GET.get("date"):
            try:
                selected_date = date.fromisoformat(request.GET["date"])
            except ValueError:
                selected_date = None
                error = "Indiquez une date au format AAAA-MM-JJ."
            else:
                if selected_date not in dates:
                    error = "Aucun élève des cars sélectionnés n’a cours à cette date."
        sheets = []
        for transport in transports:
            rows = transport_rows(registrations[transport.pk], selected_date) if selected_date and not error else []
            sheets.append(
                {
                    "transport": transport,
                    "transport_label": transport_label(transport),
                    "rows": rows,
                    "count": len(rows),
                }
            )
        ready = [sheet for sheet in sheets if sheet["count"]]
        excluded = len(sheets) - len(ready)
        if (
            request.GET.get("download") == "1"
            and ready
            and not error
            and (not excluded or request.GET.get("available") == "1")
        ):
            content = render_transport_pdf({"sheets": ready, "selected_date": selected_date})
            response = HttpResponse(content, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="cars-{selected_date.isoformat()}.pdf"'
            return response
        return render(
            request,
            "backend/registration/transports-paper-prepare.html",
            {
                "sheets": sheets,
                "ready_count": len(ready),
                "excluded_count": excluded,
                "available_dates": dates,
                "selected_date": selected_date,
                "error": error,
            },
            status=400 if error else 200,
        )
