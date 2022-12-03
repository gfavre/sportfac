from __future__ import absolute_import

import datetime

from django.contrib.auth.hashers import make_password

import factory
import factory.fuzzy
import faker
from activities.models import SCHOOL_YEARS
from schools.models import Teacher


fake = faker.Factory.create("fr_CH")


class TeacherFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Teacher

    first_name = factory.lazy_attribute(lambda o: fake.first_name())
    last_name = factory.lazy_attribute(lambda o: fake.last_name())
