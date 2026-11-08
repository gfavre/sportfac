from io import StringIO
from unittest.mock import patch

from dbtemplates.models import Template
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.urls import reverse

from api.tests.utils import UserMixin
from appointments.models import Rental
from mailer.management.commands.install_rental_invoice_email import BODY_TEMPLATE
from mailer.management.commands.install_rental_invoice_email import SUBJECT_TEMPLATE
from mailer.models import GenericEmail
from profiles.tests.factories import FamilyUserFactory
from registrations.tasks import send_bill_confirmation
from registrations.tests.factories import ChildFactory
from registrations.tests.factories import WaitingBillFactory
from sportfac.utils import TenantTestCase


class RentalInvoiceInstallationTests(UserMixin, TenantTestCase):
    def setUp(self):
        super().setUp()
        config = override_settings(KEPCHUP_USE_APPOINTMENTS=True, ROOT_URLCONF="wizard.tests.equipment_urls")
        config.enable()
        self.addCleanup(config.disable)
        self.names = (SUBJECT_TEMPLATE, BODY_TEMPLATE)
        GenericEmail.objects.filter(body_template__name=BODY_TEMPLATE).delete()
        Template.objects.filter(name__in=self.names).delete()

    def install(self, **options):
        output = StringIO()
        call_command("install_rental_invoice_email", schema=self.tenant.schema_name, stdout=output, **options)
        return output.getvalue()

    def test_dry_run_makes_no_changes_and_install_is_repeatable(self):
        with patch.object(Template, "save") as save_template, patch.object(GenericEmail, "save") as save_email:
            self.assertIn("aucune écriture", self.install(dry_run=True))
        save_template.assert_not_called()
        save_email.assert_not_called()
        self.assertFalse(Template.objects.filter(name__in=self.names).exists())
        self.install()
        self.install()
        self.assertEqual(Template.objects.filter(name__in=self.names).count(), 2)
        mail_type = GenericEmail.objects.get(body_template__name=BODY_TEMPLATE)
        self.assertEqual(mail_type.subject_template.name, SUBJECT_TEMPLATE)
        self.assertFalse(mail_type.is_html)
        self.assertIn(mail_type.get_absolute_url(), self.install())

    def test_existing_subject_body_and_mail_type_settings_are_preserved(self):
        subject = Template.objects.create(name=SUBJECT_TEMPLATE, content="Sujet personnalisé")
        body = Template.objects.create(name=BODY_TEMPLATE, content="Texte personnalisé {{ bill.total }}")
        self.install()
        mail_type = GenericEmail.objects.get(body_template=body)
        mail_type.subject = "Nom personnalisé"
        mail_type.is_html = True
        mail_type.save()
        self.install()
        subject.refresh_from_db()
        body.refresh_from_db()
        mail_type.refresh_from_db()
        self.assertEqual(subject.content, "Sujet personnalisé")
        self.assertEqual(body.content, "Texte personnalisé {{ bill.total }}")
        self.assertEqual(mail_type.subject, "Nom personnalisé")
        self.assertTrue(mail_type.is_html)

    def test_rejects_unknown_public_schema_and_disabled_feature(self):
        for schema in ("public", "not_an_existing_period"):
            with self.subTest(schema=schema), self.assertRaises(CommandError):
                call_command("install_rental_invoice_email", schema=schema, stdout=StringIO())
        with override_settings(KEPCHUP_USE_APPOINTMENTS=False), self.assertRaises(CommandError):
            self.install()
        self.assertFalse(Template.objects.filter(name__in=self.names).exists())

    def test_backend_edits_are_used_by_rental_invoice_delivery(self):
        self.install()
        mail_type = GenericEmail.objects.get(body_template__name=BODY_TEMPLATE)
        url = mail_type.get_absolute_url()
        self.assertEqual(self.tenant_client.get(url).status_code, 302)
        self.login(FamilyUserFactory())
        self.assertEqual(self.tenant_client.get(url).status_code, 302)
        self.login(FamilyUserFactory(is_staff=True))
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "rentals")
        response = self.tenant_client.post(
            url,
            {
                "subject_text": "Location {{ bill.billing_identifier }}",
                "body_text": "<p>Consultez {{ site_url }}{{ bill.get_absolute_url }}</p>",
                "is_html": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        invoice = WaitingBillFactory(payment_method="postfinance")
        Rental.objects.create(child=ChildFactory(family=invoice.family), invoice=invoice, amount=60)
        invoice.save()
        with patch("registrations.tasks.send_mail.delay") as send:
            send_bill_confirmation(
                user_pk=str(invoice.family_id),
                bill_pk=invoice.pk,
                tenant_pk=self.tenant.pk,
            )
        send.assert_called_once()
        data = send.call_args.kwargs
        self.assertEqual(data["subject"], f"Location {invoice.billing_identifier}")
        self.assertIn(invoice.get_absolute_url(), data["message"])
        self.assertIn("<p>Consultez", data["message"])
        self.assertTrue(data["is_html"])

    def test_mail_type_is_visible_in_backend_list(self):
        self.install()
        self.login(FamilyUserFactory(is_manager=True))
        response = self.tenant_client.get(reverse("backend:emails-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Facture de location de matériel")
