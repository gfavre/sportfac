from __future__ import absolute_import, unicode_literals

from django.core.files.base import ContentFile

import factory
import faker
from dbtemplates.models import Template
from profiles.tests.factories import FamilyUserFactory

from ..models import Attachment, MailArchive


fake = faker.Factory.create()


class TemplateFactory(factory.DjangoModelFactory):
    class Meta:
        model = Template

    name = factory.Faker("file_name", extension="txt")
    content = factory.Faker("paragraphs")


class MailArchiveFactory(factory.DjangoModelFactory):
    class Meta:
        model = MailArchive

    subject = factory.Faker("sentence")
    recipients = factory.LazyAttribute(
        lambda _: [
            user.pk for user in FamilyUserFactory.create_batch(factory.fuzzy.FuzzyInteger(1, 10))
        ]
    )
    bcc_recipients = factory.LazyAttribute(
        lambda _: [
            user.pk for user in FamilyUserFactory.create_batch(factory.fuzzy.FuzzyInteger(0, 3))
        ]
    )
    messages = []
    template = factory.SubFactory(TemplateFactory)


class AttachmentFactory(factory.DjangoModelFactory):
    class Meta:
        model = Attachment

    mail = factory.SubFactory(MailArchiveFactory)
    file = factory.LazyAttribute(
        lambda _: ContentFile(factory.django.FileField(filename=fake.file_name()))
    )
