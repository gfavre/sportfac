import factory.fuzzy
from faker import Faker

from ..models import PostfinanceTransaction


fake = Faker(locale="fr_CH")


class PostfinanceTransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PostfinanceTransaction

    invoice = factory.SubFactory("registrations.tests.factories.BillFactory")
    transaction_id = factory.Sequence(lambda n: f"{n}")
    payment_page_url = factory.Faker("url")
