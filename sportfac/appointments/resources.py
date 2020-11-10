# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from import_export import resources, fields

from .models import Appointment


class AppointmentResource(resources.ModelResource):
    child = fields.Field(column_name=_("Child"))

    date = fields.Field(column_name=_("Date"))
    time = fields.Field(column_name=_("Time"))
    ssf = fields.Field(column_name=_("SSF number"), attribute='child__id_lagapeo')
    has_registrations = fields.Field(column_name=_("Has registrations"))
    family = fields.Field(column_name=_("Family"))
    email = fields.Field(column_name=_("Email"))

    phone_number = fields.Field(column_name=_("Phone number"))


    class Meta:
        model = Appointment
        fields = ('date', 'time', 'child', 'ssf', 'has_registrations', 'family', 'email', 'phone_number')
        export_order = fields

    # noinspection PyMethodMayBeStatic
    def dehydrate_date(self, appointment):
        return appointment.slot.start.date()

    # noinspection PyMethodMayBeStatic
    def dehydrate_time(self, appointment):
        return appointment.slot.start.time()

    # noinspection PyMethodMayBeStatic
    def dehydrate_child(self, appointment):
        return appointment.child.full_name

    # noinspection PyMethodMayBeStatic
    def dehydrate_has_registrations(self, appointment):
        return appointment.child.has_registrations

    # noinspection PyMethodMayBeStatic
    def dehydrate_family(self, appointment):
        return appointment.family and appointment.family.full_name or ''
