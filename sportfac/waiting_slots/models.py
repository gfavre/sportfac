# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.db import connection, models, transaction
from django.urls import reverse

from registrations.models import Bill, Registration
from registrations.tasks import send_confirm_from_waiting_list

from sportfac.models import TimeStampedModel


class WaitingSlot(TimeStampedModel):
    child = models.ForeignKey("registrations.Child", on_delete=models.CASCADE)
    course = models.ForeignKey("activities.Course", on_delete=models.CASCADE)

    class Meta:
        ordering = ("course", "created")
        unique_together = (("child", "course"),)

    def get_transform_url(self):
        return reverse("backend:waiting_slot-transform", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse("backend:waiting_slot-delete", kwargs={"pk": self.pk})

    def create_registration(self, send_confirmation=True):
        registration = Registration.objects.create(
            course=self.course, child=self.child, status=Registration.STATUS.confirmed
        )
        registration.price = registration.get_price()
        if registration.price == 0:
            registration.paid = True
        bill = Bill.objects.create(
            status=Bill.STATUS.waiting,
            family=self.child.family,
            payment_method=settings.KEPCHUP_PAYMENT_METHOD,
        )
        registration.bill = bill
        registration.save()
        if send_confirmation:
            try:
                tenant_pk = connection.tenant.pk
            except AttributeError:
                tenant_pk = None
            transaction.on_commit(
                lambda: send_confirm_from_waiting_list.delay(registration.pk, tenant_pk)
            )

    def __repr__(self):
        return self.__unicode__()

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return "{} - {}".format(self.child, self.course.short_name)
