from __future__ import absolute_import
import datetime

from django.conf import settings

import factory
import factory.fuzzy
import faker

from activities.models import Activity, AllocationAccount, Course, SCHOOL_YEARS


fake = faker.Factory.create()

YEARS = [year for (year, name) in SCHOOL_YEARS]


class AllocationAccountFactory(factory.DjangoModelFactory):
    class Meta:
        model = AllocationAccount

    account = factory.Sequence(lambda n: 'account-{}'.format(n))
    name = factory.Faker('bs')


class ActivityFactory(factory.DjangoModelFactory):
    class Meta:
        model = Activity

    number = factory.Sequence(lambda x: "{0}".format(x))
    name = factory.lazy_attribute(lambda o: fake.word())
    description = factory.lazy_attribute(lambda o: fake.text())
    informations = factory.lazy_attribute(lambda o: fake.text())


class CourseFactory(factory.DjangoModelFactory):
    class Meta:
        model = Course

    activity = factory.SubFactory(ActivityFactory)

    number = factory.Sequence(lambda x: "{0}".format(x))
    number_of_sessions = factory.fuzzy.FuzzyInteger(0, 42)
    start_date = factory.fuzzy.FuzzyDate(start_date=datetime.date(2014, 1, 1))
    end_date = factory.LazyAttribute(
        lambda c: c.start_date + datetime.timedelta(days=90)
    )
    start_time = datetime.time(hour=16)
    end_time = datetime.time(hour=17)
    place = factory.lazy_attribute(lambda o: fake.address())
    min_participants = factory.fuzzy.FuzzyInteger(1, 20)

    max_participants = factory.LazyAttribute(
        lambda c: c.min_participants + 5
    )
    schoolyear_min = factory.fuzzy.FuzzyChoice(YEARS[:-1])
    schoolyear_max = factory.fuzzy.FuzzyChoice(YEARS[1:])

    price = factory.fuzzy.FuzzyInteger(1, 100)
    price_local = factory.fuzzy.FuzzyInteger(1, 100)
    price_family = factory.fuzzy.FuzzyInteger(1, 100)
    price_local_family = factory.fuzzy.FuzzyInteger(1, 100)
    price_description = factory.lazy_attribute(lambda o: fake.text())
    age_min = factory.fuzzy.FuzzyInteger(settings.KEPCHUP_AGES[0], settings.KEPCHUP_AGES[-1] - 1)
    age_max = factory.LazyAttribute(lambda o: o.age_min + 1)

    comments = factory.lazy_attribute(lambda o: fake.text())


    @factory.post_generation
    def instructors(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for instructor in extracted:
                self.instructors.add(instructor)
