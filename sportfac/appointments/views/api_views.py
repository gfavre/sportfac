from django.contrib import messages
from django.db import connection, transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import get_language
from django.utils.translation import gettext as _

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from api.permissions import ManagerPermission
from registrations.models import Child
from ..models import Appointment, AppointmentSlot, AppointmentType, Rental
from ..serializers import AdminAppointmentSlotSerializer, AppointmentSerializer, RentalSerializer, SlotSerializer
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
                "appointment_type": AppointmentType.objects.filter(start__lte=slot.start, end__gte=slot.end).first(),
            }
            if request.user.is_authenticated:
                defaults["family"] = request.user

            appointment, created = Appointment.objects.update_or_create(child=child, slot=slot, defaults=defaults)
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
                _("Your appointment is registered."),
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


class RentalViewSet(ModelViewSet):
    queryset = Rental.objects.all()
    serializer_class = RentalSerializer

    def destroy(self, request, *args, **kwargs):
        """Delete a rental if no pickup or return appointment is set."""
        child_id = kwargs.get("pk")
        try:
            rental = Rental.objects.get(child__id=child_id)

            # Check if the rental has any appointments set
            if rental.pickup_appointment or rental.return_appointment:
                return Response(
                    {"success": False, "message": "Cannot delete rental with set appointments."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            rental.delete()
            return Response({"success": True, "message": "Rental deleted successfully."}, status=status.HTTP_200_OK)
        except Rental.DoesNotExist:
            return Response({"success": False, "message": "Rental does not exist."}, status=status.HTTP_404_NOT_FOUND)
