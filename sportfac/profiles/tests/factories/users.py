import datetime

from django.contrib.auth.hashers import make_password

import factory
import factory.fuzzy


from profiles.models import FamilyUser, Child, Registration, SchoolYear, Teacher
from activities.models import SCHOOL_YEARS


YEARS = [year for (year, name) in SCHOOL_YEARS]
DEFAULT_PASS = 'test'

class FamilyUserFactory(factory.DjangoModelFactory):
    class Meta:
        model = FamilyUser

    email = factory.Sequence(lambda x: "test{0}@kepchup.ch".format(x))
    password = make_password(DEFAULT_PASS)
    first_name = factory.fuzzy.FuzzyText()
    last_name = factory.fuzzy.FuzzyText()
    zipcode = factory.fuzzy.FuzzyText(length=5)
    city = factory.fuzzy.FuzzyText()
    country = 'CH'


class SchoolYearFactory(factory.DjangoModelFactory):
    class Meta:
        model = SchoolYear
    
    year = factory.fuzzy.FuzzyChoice(YEARS[:-1])


class TeacherFactory(factory.DjangoModelFactory):
    class Meta:
        model = Teacher
    
    first_name = factory.fuzzy.FuzzyText()
    last_name = factory.fuzzy.FuzzyText()


class ChildFactory(factory.DjangoModelFactory):
    class Meta:
        model = Child
    
    first_name = factory.fuzzy.FuzzyText()
    last_name = factory.fuzzy.FuzzyText()
    sex = 'M'
    birth_date = factory.fuzzy.FuzzyDate(start_date=datetime.date(2008, 1, 1))
    school_year = factory.SubFactory(SchoolYearFactory)
    teacher = factory.SubFactory(TeacherFactory)
    family = factory.SubFactory(FamilyUserFactory)
