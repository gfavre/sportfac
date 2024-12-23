import datetime

from django.conf import settings

import factory.fuzzy
from activities.models import SCHOOL_YEARS, Activity, AllocationAccount, Course, CoursesInstructors, ExtraNeed
from faker import Faker
from profiles.tests.factories import FamilyUserFactory


fake = Faker()

YEARS = [year for (year, name) in SCHOOL_YEARS]


class AllocationAccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AllocationAccount

    account = factory.Sequence(lambda n: f"account-{n}")
    name = factory.Faker("bs")


class ActivityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Activity

    number = factory.Sequence(lambda a: f"{a}")
    name = factory.Sequence(lambda a: fake.word() + f" -{a}")
    description = factory.Faker("text")
    informations = factory.Faker("text")


class CourseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Course

    activity = factory.SubFactory(ActivityFactory)
    name = factory.Faker("word")
    number = factory.Sequence(lambda x: f"{x}")
    number_of_sessions = factory.fuzzy.FuzzyInteger(0, 42)
    start_date = factory.fuzzy.FuzzyDate(start_date=datetime.date(2014, 1, 1))
    end_date = factory.LazyAttribute(lambda c: c.start_date + datetime.timedelta(days=90))
    start_time = datetime.time(hour=16)
    end_time = datetime.time(hour=17)
    place = factory.Faker("address", locale="fr_CH")
    min_participants = factory.fuzzy.FuzzyInteger(1, 20)

    max_participants = factory.LazyAttribute(lambda c: c.min_participants + 5)
    schoolyear_min = factory.fuzzy.FuzzyChoice(YEARS[:-1])
    schoolyear_max = factory.fuzzy.FuzzyChoice(YEARS[1:])

    price = factory.fuzzy.FuzzyInteger(50, 200)
    price_local = factory.LazyAttribute(lambda c: c.price - 10)
    price_family = factory.LazyAttribute(lambda c: c.price - 5)
    price_local_family = factory.LazyAttribute(lambda c: c.price - 15)
    price_description = factory.Faker("text")
    age_min = factory.fuzzy.FuzzyInteger(settings.KEPCHUP_AGES[0], settings.KEPCHUP_AGES[-1] - 1)
    age_max = factory.LazyAttribute(lambda o: o.age_min + 1)
    visible = True

    comments = factory.Faker("text")

    @factory.post_generation
    def instructors(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for instructor in extracted:
                CoursesInstructorsFactory(course=self, instructor=instructor)


class CoursesInstructorsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CoursesInstructors

    course = factory.SubFactory(CourseFactory)
    instructor = factory.SubFactory(FamilyUserFactory)


class ExtraNeedFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ExtraNeed

    question_label = factory.Faker("sentence")
