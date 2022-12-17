import datetime

from django.contrib.auth.hashers import make_password

import factory.fuzzy
import faker
from activities.models import SCHOOL_YEARS
from profiles.models import City, FamilyUser, SchoolYear


YEARS = [year for (year, name) in SCHOOL_YEARS]
DEFAULT_PASS = "test"

fake = faker.Factory.create("fr_CH")


class SchoolYearFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SchoolYear

    year = factory.fuzzy.FuzzyChoice(YEARS[:-1])


class FamilyUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FamilyUser

    email = factory.Sequence(lambda x: "test{0}@kepchup.ch".format(x))
    password = make_password(DEFAULT_PASS)
    first_name = factory.lazy_attribute(lambda o: fake.first_name())
    last_name = factory.lazy_attribute(lambda o: fake.last_name())
    address = factory.lazy_attribute(lambda o: fake.address())
    zipcode = factory.lazy_attribute(lambda o: fake.postcode())
    city = factory.lazy_attribute(lambda o: fake.city())

    country = "CH"
    private_phone = factory.lazy_attribute(lambda o: fake.phone_number())


class CityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = City

    zipcode = factory.lazy_attribute(lambda o: fake.postcode())
    name = factory.lazy_attribute(lambda o: fake.city())
