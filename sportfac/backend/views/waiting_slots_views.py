# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from django.views.generic import DeleteView, UpdateView

from waiting_slots.forms import WaitingSlotTransformForm
from waiting_slots.models import WaitingSlot

from .mixins import BackendMixin


class WaitingSlotTransformView(SuccessMessageMixin, BackendMixin, UpdateView):
    """
    Transform a waitingslot to a proper registration.
    """

    model = WaitingSlot
    template_name = "backend/waiting_slots/confirm_move.html"
    pk_url_kwarg = "pk"
    form_class = WaitingSlotTransformForm

    def get_success_url(self):
        return self.object.course.get_backend_url()

    # noinspection PyAttributeOutsideInit
    def form_valid(self, form):
        self.object = self.get_object()
        self.object.create_registration(send_confirmation=form.cleaned_data["send_confirmation"])
        return self.delete()

    # noinspection PyAttributeOutsideInit
    def delete(self):
        success_url = self.get_success_url()
        child = self.object.child
        self.object.delete()
        messages.success(
            self.request,
            _(
                "%(child)s has been added to participants and removed from waiting list. "
                "Please contact the parents."
            )
            % {"child": child.get_full_name()},
        )
        return HttpResponseRedirect(success_url)


class WaitingSlotDeleteView(SuccessMessageMixin, BackendMixin, DeleteView):
    model = WaitingSlot
    template_name = "backend/waiting_slots/confirm_delete.html"
    pk_url_kwarg = "pk"

    def get_success_url(self):
        return self.object.course.get_backend_url()
