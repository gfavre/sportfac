from django.contrib import messages
from django.db import connection, transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import get_language
from django.utils.translation import gettext as _

from rest_framework import generics, mixins, status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from api.permissions import ManagerPermission
from registrations.models import Child
from ..models import Appointment, AppointmentSlot, AppointmentType, Rental
from ..serializers import (
    AdminAppointmentSlotSerializer,
    AppointmentSerializer,
    RegisterChildrenSerializer,
    RentalSerializer,
    SlotSerializer,
)
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


class RentalListView(generics.ListAPIView):
    serializer_class = RentalSerializer

    def get_queryset(self):
        return Rental.objects.filter(child__family=self.request.user)


class AppointmentManagementView(mixins.CreateModelMixin, mixins.DestroyModelMixin, generics.GenericAPIView):
    """
    ModelViewSet to handle managing appointments and updating rentals accordingly.
    """

    queryset = AppointmentSlot.objects.filter(start__gte=now())
    serializer_class = RegisterChildrenSerializer

    def get_serializer_context(self):
        return {"request": self.request}

    def get_object(self):
        """
        Fetch AppointmentSlot using slot_id from the URL.
        """
        slot_id = self.kwargs.get("slot_id")
        return get_object_or_404(AppointmentSlot, id=slot_id)

    def manage_appointment(self, child_id, slot, appointment_type, action="create"):
        """
        Helper method to create, update, or remove appointments and adjust rentals.
        Returns the modified Rental instance or None if not modified.
        """
        try:
            child = Child.objects.get(id=child_id, family=self.request.user)
            rental = Rental.objects.get(child=child)

            if action == "create":
                appointment, _ = Appointment.objects.get_or_create(slot=slot, child=child)
                if appointment_type == "pickup":
                    rental.pickup_appointment = appointment
                elif appointment_type == "return":
                    rental.return_appointment = appointment
                rental.save()
                return rental

            if action == "remove":
                appointment = Appointment.objects.get(slot=slot, child=child)
                appointment.delete()
                rental.refresh_from_db()
                return rental

        except (Child.DoesNotExist, Rental.DoesNotExist, Appointment.DoesNotExist):
            return None  # Skip if child, rental, or appointment does not exist

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """
        Handle creating or updating child appointments for a given slot.
        Returns the updated rentals.
        """
        serializer = self.get_serializer(data=request.data, context=self.get_serializer_context())
        if serializer.is_valid():
            slot = self.get_object()
            appointment_type = serializer.validated_data["appointment_type"]
            children_ids = serializer.validated_data["children"]

            updated_rentals = []

            for child_id in children_ids:
                rental = self.manage_appointment(child_id, slot, appointment_type, action="create")
                if rental:
                    updated_rentals.append(rental)

            rental_serializer = RentalSerializer(updated_rentals, many=True)
            return Response(
                {"message": "Children successfully registered to the slot.", "rentals": rental_serializer.data},
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Handle removing child appointments from a given slot.
        Returns the updated rentals.
        """
        serializer = self.get_serializer(data=request.data, context=self.get_serializer_context())
        if serializer.is_valid():
            slot = self.get_object()
            appointment_type = serializer.validated_data["appointment_type"]
            children_ids = serializer.validated_data["children"]
            updated_rentals = []

            for child_id in children_ids:
                rental = self.manage_appointment(child_id, slot, appointment_type, action="remove")
                if rental:
                    updated_rentals.append(rental)

            rental_serializer = RentalSerializer(updated_rentals, many=True)
            return Response(
                {"message": "Rental(s) successfully removed.", "rentals": rental_serializer.data},
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RemoveChildFromSlotView(generics.GenericAPIView):
    serializer_class = RegisterChildrenSerializer

    def get_queryset(self):
        return AppointmentSlot.objects.filter(start__gte=now())

    def delete(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        if serializer.is_valid():
            children_ids = serializer.validated_data["children"]
            slot = serializer.validated_data["slot"]
            appointment_type = serializer.validated_data["appointment_type"]

            # Remove associations for each child
            for child_id in children_ids:
                try:
                    appointment = Appointment.objects.get(child__id=child_id, slot=slot)
                    appointment.delete()
                    rental = Rental.objects.get(child__id=child_id)
                    if appointment_type == "pickup" and rental.pickup_appointment == slot:
                        rental.pickup_appointment = None
                    elif appointment_type == "return" and rental.return_appointment == slot:
                        rental.return_appointment = None
                    rental.save()

                except Rental.DoesNotExist:
                    continue  # Skip if no existing rental
                except Appointment.DoesNotExist:
                    continue

            return Response({"message": "Rental(s) successfully removed."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegisterChildrenToSlotView(generics.GenericAPIView):
    serializer_class = RegisterChildrenSerializer

    def get_queryset(self):
        return AppointmentSlot.objects.filter(start__gte=now())

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        if serializer.is_valid():
            children_ids = serializer.validated_data["children"]
            slot = serializer.validated_data["slot"]
            appointment_type = serializer.validated_data["appointment_type"]
            for child in children_ids:
                child = Child.objects.get(id=child)
                appointment, _ = Appointment.objects.get_or_create(
                    slot=slot,
                    child=child,
                )
                if appointment_type:
                    rental = Rental.objects.get(child=child)
                    if appointment_type == "pickup":
                        rental.pickup_appointment = appointment
                    elif appointment_type == "return":
                        rental.return_appointment = appointment
                    rental.save()

            return Response(
                {"message": "Children successfully registered to the slot."}, status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
