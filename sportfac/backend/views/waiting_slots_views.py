# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db import IntegrityError
from django.urls import reverse_lazy
from django.utils.translation import ugettext as _
from django.views.generic import DeleteView

from .mixins import BackendMixin

from registrations.models import Bill
from waiting_slots.models import WaitingSlot


class WaitingSlotTransformView(SuccessMessageMixin, BackendMixin, DeleteView):
    """
    Transform a waitingslot to a proper registration.
    """
    model = WaitingSlot
    success_url = reverse_lazy('backend:activity-list')
    template_name = 'backend/waiting_slots/confirm_delete.html'
    pk_url_kwarg = 'pk'

    def get_success_url(self):
        return self.object.course.get_backend_url()

    # noinspection PyAttributeOutsideInit
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        child = self.object.child
        try:
            registration = self.object.create_registration()
            registration.price = registration.get_price()
            if registration.price == 0:
                registration.paid = True
            bill = Bill.objects.create(
                status=Bill.STATUS.waiting,
                family=child.family,
                payment_method=settings.KEPCHUP_PAYMENT_METHOD,
            )
            registration.bill = bill
            registration.save()
        except IntegrityError:
            # There is an already existing registration for this child and course.
            pass
        messages.success(self.request,
                         _("%(child)s has been added to participants and removed from waiting list. "
                           "Please contact the parents.") % {
                             'child': child.get_full_name()
                         })
        return super(WaitingSlotTransformView, self).delete(request, *args, **kwargs)
