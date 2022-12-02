# -*- coding: utf-8 -*-
from __future__ import absolute_import
import datetime

from django.utils import timezone

import factory.fuzzy

from ..models import Appointment, AppointmentSlot


class AppointmentSlotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AppointmentSlot

    title = factory.Faker('bs')
    places = factory.fuzzy.FuzzyInteger(1, 5)
    start = factory.Faker('future_datetime', tzinfo=timezone.get_current_timezone())
    end = factory.lazy_attribute(lambda o: o.start + datetime.timedelta(hours=1))


class AppointmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Appointment

    slot = factory.SubFactory(AppointmentSlotFactory)
    child = factory.SubFactory('registrations.tests.factories.ChildFactory')
    family = factory.lazy_attribute(lambda a: a.child.family)
    email = factory.Faker('email', locale='fr_CH')
    phone_number = factory.Faker('phone_number', locale='fr_CH')

