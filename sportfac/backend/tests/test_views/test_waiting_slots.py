# -*- coding: utf-8 -*-
from django.contrib.messages.storage import default_storage
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import reverse

import mock

from profiles.tests.factories import FamilyUserFactory
from registrations.models import Registration, Bill
from sportfac.utils import TenantTestCase
from waiting_slots.models import WaitingSlot
from waiting_slots.tests.factories import WaitingSlotFactory
from ...views.waiting_slots_views import (
    WaitingSlotTransformView
)
from .base import fake_registrations_open_middleware


class WaitingSlotTransformViewTests(TenantTestCase):
    def setUp(self):
        super(WaitingSlotTransformViewTests, self).setUp()
        self.user = FamilyUserFactory(is_manager=True)
        self.waiting_slot = WaitingSlotFactory()
        self.login_url = reverse('login')
        self.url = reverse('backend:waiting_slot-transform', kwargs={'pk': self.waiting_slot.pk})
        self.view = WaitingSlotTransformView.as_view()
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user
        self.request._messages = mock.MagicMock()

    def get_response(self, request):
        return self.view(request, pk=self.waiting_slot.pk)

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.get_response(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "/?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.get_response(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "/?next=" + self.url))

    def test_get_is_200(self):
        response = self.get_response(self.request)
        self.assertEqual(response.status_code, 200)

    def test_post_creates_registration(self):
        data = {"send_confirmation": False}
        request = RequestFactory().post(self.url, data=data)
        fake_registrations_open_middleware(request)
        request.user = self.user
        request._messages = mock.MagicMock()

        response = self.get_response(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Registration.objects.count(), 1)
        self.assertEqual(Bill.objects.count(), 1)
        self.assertEqual(WaitingSlot.objects.count(), 0)

    @mock.patch('waiting_slots.models.send_confirm_from_waiting_list.delay')
    def test_post_sends_email(self, mock_send_confirm_from_waiting_list):
        data = {"send_confirmation": True}
        request = RequestFactory().post(self.url, data=data)
        fake_registrations_open_middleware(request)
        request.user = self.user
        request._messages = mock.MagicMock()

        response = self.get_response(request)
        self.assertEqual(response.status_code, 302)
        mock_send_confirm_from_waiting_list.assert_called_once
