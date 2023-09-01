# -*- coding: utf-8 -*-
from django.contrib import messages
from django.db import connection, transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import get_language
from django.utils.translation import gettext as _

from api.permissions import ManagerPermission
from registrations.models import Child
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from ..models import Appointment, AppointmentSlot
from ..serializers import AdminAppointmentSlotSerializer, AppointmentSerializer, SlotSerializer
from ..tasks import send_confirmation_mail as send_appointment_confirmation_email


class SlotsList(generics.ListAPIView):
    serializer_class = SlotSerializer

    def get_queryset(self):
        return AppointmentSlot.objects.filter(start__gte=now())


class RegisterSlot(generics.GenericAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = ()

    def get_queryset(self):
        return AppointmentSlot.objects.filter(start__gte=now())

    def post(self, request, *args, **kwargs):
        slot = get_object_or_404(self.get_queryset(), id=kwargs.get("slot_id"))
        serializer = AppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        total = 0
        appointments = []
        for child_id in serializer.data["children"]:
            child = get_object_or_404(Child.objects.all(), id=child_id)
            defaults = {
                "phone_number": serializer.validated_data["phone"],
                "email": serializer.validated_data["email"],
                "slot": slot,
            }
            if request.user.is_authenticated:
                defaults["family"] = request.user

            appointment, created = Appointment.objects.update_or_create(
                child=child, defaults=defaults
            )
            appointments.append(appointment)
            if created:
                total += 1
        data = {"total": total}
        if self.request.user.is_authenticated:
            user = str(self.request.user.pk)
            data["url"] = serializer.validated_data["url"] or reverse("appointments:register")
            messages.add_message(
                request,
                messages.SUCCESS,
                _(" Your appointment is registered. You should receive a reminder email shortly."),
            )

        else:
            user = None
            data["url"] = reverse("appointments:success")
        if not serializer.validated_data["url"].endswith(reverse("wizard_appointments")):
            # appointment info is included in wizard's end email
            try:
                tenant_pk = connection.tenant.pk
            except AttributeError:
                tenant_pk = None
            transaction.on_commit(
                lambda: send_appointment_confirmation_email.delay(
                    [appointment.pk for appointment in appointments],
                    tenant_pk,
                    user=user,
                    language=get_language(),
                )
            )
        return Response(data, status=status.HTTP_201_CREATED)


class SlotsViewset(ModelViewSet):
    permission_classes = (ManagerPermission,)
    queryset = AppointmentSlot.objects.all()
    serializer_class = AdminAppointmentSlotSerializer

    def get_queryset(self):
        return AppointmentSlot.objects.filter(start__gte=now())
