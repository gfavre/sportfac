import datetime

import factory
import factory.fuzzy
import faker

from activities.models import Activity, Course, SCHOOL_YEARS


fake = faker.Factory.create()

YEARS = [year for (year, name) in SCHOOL_YEARS]


class ActivityFactory(factory.DjangoModelFactory):
    class Meta:
        model = Activity

    number = factory.Sequence(lambda x: "{0}".format(x))
    name = factory.lazy_attribute(lambda o: fake.word())


class CourseFactory(factory.DjangoModelFactory):
    class Meta:
        model = Course

    activity = factory.SubFactory(ActivityFactory)

    number = factory.Sequence(lambda x: "{0}".format(x))
    number_of_sessions = factory.fuzzy.FuzzyInteger(0, 42)
    start_date = factory.fuzzy.FuzzyDate(start_date=datetime.date(2014,1,1))
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

    @factory.post_generation
    def instructors(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for instructor in extracted:
                self.instructors.add(instructor)
