import datetime

import factory
import factory.fuzzy
import faker

from activities.tests.factories import CourseFactory
from profiles.tests.factories import FamilyUserFactory, SchoolYearFactory
from registrations.models import Registration, Child, Bill
from schools.tests.factories import TeacherFactory

fake = faker.Factory.create('fr_CH')


class ChildFactory(factory.DjangoModelFactory):
    class Meta:
        model = Child

    first_name = factory.lazy_attribute(lambda o: fake.first_name())
    last_name = factory.lazy_attribute(lambda o: fake.last_name())
    sex = factory.fuzzy.FuzzyChoice(('M', 'F'))
    birth_date = factory.fuzzy.FuzzyDate(start_date=datetime.date(2008, 1, 1))
    #school_year = factory.SubFactory(SchoolYearFactory)
    #teacher = factory.SubFactory(TeacherFactory)
    family = factory.SubFactory(FamilyUserFactory)


class RegistrationFactory(factory.DjangoModelFactory):
    class Meta:
        model = Registration

    course = factory.SubFactory(CourseFactory)
    child = factory.SubFactory(ChildFactory)


class WaitingRegistrationFactory(RegistrationFactory):
    class Meta:
        model = Registration

    status = Registration.STATUS.waiting


class BillFactory(factory.DjangoModelFactory):
    class Meta:
        model = Bill

    billing_identifier = factory.fuzzy.FuzzyText(length=10)
    family = factory.SubFactory(FamilyUserFactory)

    @factory.post_generation
    def registrations(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for registration in extracted:
                self.registrations.add(registration)


class WaitingBillFactory(BillFactory):
    class Meta:
        model = Bill

    status = Bill.STATUS.waiting
