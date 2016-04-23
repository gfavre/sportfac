import datetime

from django.contrib.auth.hashers import make_password

import factory
import factory.fuzzy
import faker


from profiles.models import FamilyUser, Child, Registration, SchoolYear, Teacher
from activities.models import SCHOOL_YEARS


fake = faker.Factory.create('fr_CH')

YEARS = [year for (year, name) in SCHOOL_YEARS]
DEFAULT_PASS = 'test'

class FamilyUserFactory(factory.DjangoModelFactory):
    class Meta:
        model = FamilyUser

    email = factory.Sequence(lambda x: "test{0}@kepchup.ch".format(x))
    password = make_password(DEFAULT_PASS)
    first_name = factory.lazy_attribute(lambda o: fake.first_name())
    last_name = factory.lazy_attribute(lambda o: fake.last_name())
    zipcode = factory.lazy_attribute(lambda o: fake.postcode())
    city = factory.lazy_attribute(lambda o: fake.city())
    country = 'CH'


class SchoolYearFactory(factory.DjangoModelFactory):
    class Meta:
        model = SchoolYear
    
    year = factory.fuzzy.FuzzyChoice(YEARS[:-1])


class TeacherFactory(factory.DjangoModelFactory):
    class Meta:
        model = Teacher
    
    first_name = factory.lazy_attribute(lambda o: fake.first_name())
    last_name = factory.lazy_attribute(lambda o: fake.last_name())


class ChildFactory(factory.DjangoModelFactory):
    class Meta:
        model = Child
    
    first_name = factory.lazy_attribute(lambda o: fake.first_name())
    last_name = factory.lazy_attribute(lambda o: fake.last_name())
    sex = factory.fuzzy.FuzzyChoice(('M', 'F'))
    birth_date = factory.fuzzy.FuzzyDate(start_date=datetime.date(2008, 1, 1))
    school_year = factory.SubFactory(SchoolYearFactory)
    teacher = factory.SubFactory(TeacherFactory)
    family = factory.SubFactory(FamilyUserFactory)
