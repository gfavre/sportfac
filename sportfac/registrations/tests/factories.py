import datetime
from pathlib import Path

import factory.fuzzy
from activities.tests.factories import CourseFactory, ExtraNeedFactory
from faker import Faker
from profiles.tests.factories import FamilyUserFactory
from registrations.models import Bill, Child, ExtraInfo, Registration


fake = Faker(locale="fr_CH")
FIXTURES_PATH = Path(__file__).parent / "media_fixtures"
BILL_PATH = FIXTURES_PATH / "bill.pdf"


class ChildFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Child

    first_name = factory.lazy_attribute(lambda o: fake.first_name())
    last_name = factory.lazy_attribute(lambda o: fake.last_name())
    sex = factory.fuzzy.FuzzyChoice(("M", "F"))
    birth_date = factory.fuzzy.FuzzyDate(start_date=datetime.date(2008, 1, 1))
    # school_year = factory.SubFactory(SchoolYearFactory)
    # teacher = factory.SubFactory(TeacherFactory)
    family = factory.SubFactory(FamilyUserFactory)


class RegistrationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Registration

    course = factory.SubFactory(CourseFactory)
    child = factory.SubFactory(ChildFactory)


class WaitingRegistrationFactory(RegistrationFactory):
    class Meta:
        model = Registration

    status = Registration.STATUS.waiting


class BillFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Bill

    billing_identifier = factory.fuzzy.FuzzyText(length=10)
    family = factory.SubFactory(FamilyUserFactory)
    pdf = factory.django.FileField(from_path=BILL_PATH)

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


class ExtraInfoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ExtraInfo

    registration = factory.SubFactory(RegistrationFactory)
    key = factory.SubFactory(ExtraNeedFactory)
    value = factory.Faker("sentence")
