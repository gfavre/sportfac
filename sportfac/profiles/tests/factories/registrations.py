import datetime

import factory
import factory.fuzzy

from activities.tests.factories import CourseFactory
from profiles.models import Registration
from .users import ChildFactory





class RegistrationFactory(factory.DjangoModelFactory):
    class Meta:
        model = Registration
    
    course = factory.SubFactory(CourseFactory)
    child = factory.SubFactory(ChildFactory)