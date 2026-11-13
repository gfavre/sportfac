from django.test import override_settings
from django.utils import timezone

from appointments.models import Rental
from appointments.tests.factories import AppointmentFactory
from registrations.resources import RegistrationResource
from sportfac.utils import TenantTestCase

from .factories import RegistrationFactory


class RegistrationResourceTests(TenantTestCase):
    @override_settings(KEPCHUP_USE_APPOINTMENTS=False)
    def test_rental_columns_are_hidden_when_disabled(self):
        resource = RegistrationResource()
        for name in ("rental", "pickup_appointment", "return_appointment"):
            self.assertNotIn(name, resource.fields)
            self.assertNotIn(name, resource.get_export_order())

    @override_settings(KEPCHUP_USE_APPOINTMENTS=True)
    def test_export_uses_each_childs_rental_appointments(self):
        registration = RegistrationFactory()
        other = RegistrationFactory()
        pickup = AppointmentFactory(child=registration.child)
        returning = AppointmentFactory(child=registration.child, slot__appointment_type="return")
        Rental.objects.create(child=registration.child, pickup_appointment=pickup, return_appointment=returning)
        resource = RegistrationResource()
        data = resource.export(resource.get_queryset().filter(pk__in=[registration.pk, other.pk]).order_by("pk"))
        pickup_index = resource.get_export_order().index("pickup_appointment")
        return_index = resource.get_export_order().index("return_appointment")
        self.assertEqual(data[0][pickup_index], timezone.localtime(pickup.slot.start).strftime("%d.%m.%Y %H:%M"))
        self.assertEqual(data[0][return_index], timezone.localtime(returning.slot.start).strftime("%d.%m.%Y %H:%M"))
        self.assertEqual(data[1][pickup_index], "")
        self.assertEqual(data[1][return_index], "")

    @override_settings(KEPCHUP_USE_APPOINTMENTS=True)
    def test_rental_without_appointments_exports_empty_dates(self):
        registration = RegistrationFactory()
        Rental.objects.create(child=registration.child)
        resource = RegistrationResource()
        self.assertEqual(resource.dehydrate_pickup_appointment(registration), "")
        self.assertEqual(resource.dehydrate_return_appointment(registration), "")
