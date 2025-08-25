import factory.fuzzy

from ..models import WizardStep


class WizardStepFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WizardStep

    title = factory.Faker("bs")
    subtitle = factory.Faker("bs")
    lead = factory.Faker("sentence")
    description = factory.Faker("paragraph")
    order = factory.Sequence(lambda n: n)
