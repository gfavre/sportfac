from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.test import override_settings

from backend.views.registration_views import TransportDetailView
from profiles.tests.factories import FamilyUserFactory
from registrations.models import Transport
from registrations.tests.factories import RegistrationFactory
from sportfac.utils import TenantTestCase

from .base import fake_registrations_open_middleware


@override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=False)
class TransportDetailTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.transport = Transport.objects.create(name="Car bleu")

    def response(self, user):
        request = RequestFactory().get(self.transport.backend_url)
        request.user = user
        fake_registrations_open_middleware(request)
        return TransportDetailView.as_view()(request, pk=self.transport.pk)

    def test_parent_name_is_in_printable_contact_cell(self):
        RegistrationFactory(
            transport=self.transport, child__family__first_name="Camille", child__family__last_name="Durand"
        )
        response = self.response(FamilyUserFactory(is_manager=True))
        self.assertContains(response, "Parent / téléphone", status_code=200)
        self.assertContains(response, '<span class="parent-name">Camille Durand</span>', html=True)

    def test_missing_family_is_displayed_without_error(self):
        RegistrationFactory(transport=self.transport, child__family=None)
        response = self.response(FamilyUserFactory(is_manager=True))
        self.assertContains(response, "Parent non renseigné", status_code=200)

    def test_parent_names_are_prefetched(self):
        RegistrationFactory.create_batch(3, transport=self.transport)
        transport = TransportDetailView.queryset.get(pk=self.transport.pk)
        with self.assertNumQueries(0):
            names = [registration.child.family.get_full_name() for registration in transport.participants.all()]
        self.assertEqual(len(names), 3)

    def test_anonymous_and_parent_cannot_access_driver_list(self):
        for user in (AnonymousUser(), FamilyUserFactory(), FamilyUserFactory(is_restricted_manager=True)):
            with self.subTest(user=user):
                self.assertEqual(self.response(user).status_code, 302)
