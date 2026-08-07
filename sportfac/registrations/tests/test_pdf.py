import fitz

from backend.dynamic_preferences_registry import global_preferences_registry
from sportfac.utils import TenantTestCase

from ..pdf import generate_pdf_for_bill
from .factories import BillFactory


class GeneratePdfForBillTestCase(TenantTestCase):
    def setUp(self):
        super().setUp()
        preferences = global_preferences_registry.manager()
        preferences["payment__IBAN"] = "CH9300762011623852957"
        preferences["payment__ADDRESS"] = "Commune de Coppet\nGrand-Rue 34\n1296 Coppet"

    def test_generates_pdf_without_qr_invoice(self):
        bill = BillFactory(payment_method="external")
        bill.save()
        self.assertEqual(bill.qr_invoice, "")

        pdf_bytes = generate_pdf_for_bill(bill)

        self.assertIsNotNone(pdf_bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_generates_pdf_with_qr_invoice_pinned_to_bottom(self):
        bill = BillFactory(payment_method="iban")
        bill.save()
        self.assertIn("<svg", bill.qr_invoice)

        pdf_bytes = generate_pdf_for_bill(bill)

        self.assertIsNotNone(pdf_bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            self.assertGreaterEqual(doc.page_count, 1)
            last_page_text = doc[-1].get_text()
            self.assertIn("Section paiement", last_page_text)  # QR-bill "Payment part" label, in French
