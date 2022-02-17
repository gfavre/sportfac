import datetime

import factory.fuzzy

from ..models import Absence, Session


class SessionFactory(factory.django.DjangoModelFactory):
    course = factory.SubFactory('activities.tests.factories.CourseFactory')
    date = factory.fuzzy.FuzzyDate(start_date=datetime.date(2022, 1, 1))

    class Meta:
        model = Session


class AbsenceFactory(factory.django.DjangoModelFactory):
    child = factory.SubFactory('registrations.tests.factories.ChildFactory')
    session = factory.SubFactory(SessionFactory)

    class Meta:
        model = Absence

