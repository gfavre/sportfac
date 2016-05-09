import datetime

import factory
import factory.fuzzy
import faker

from activities.tests.factories import CourseFactory
from profiles.tests.factories import FamilyUserFactory, SchoolYearFactory
from registrations.models import Registration, Child
from schools.tests.factories import TeacherFactory

fake = faker.Factory.create('fr_CH')

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


class RegistrationFactory(factory.DjangoModelFactory):
    class Meta:
        model = Registration
    
    course = factory.SubFactory(CourseFactory)
    child = factory.SubFactory(ChildFactory)
    
