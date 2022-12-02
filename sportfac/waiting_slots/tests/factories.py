from __future__ import absolute_import
import factory.fuzzy

from ..models import WaitingSlot


class WaitingSlotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WaitingSlot

    course = factory.SubFactory('activities.tests.factories.CourseFactory')
    child = factory.SubFactory('registrations.tests.factories.ChildFactory')
