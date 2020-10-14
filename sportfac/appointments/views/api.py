# -*- coding: utf-8 -*-
from django.shortcuts import get_object_or_404

from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response

from registrations.models import Child
from ..models import AppointmentSlot, Appointment
from ..serializers import SlotSerializer, AppointmentSerializer


class SlotsList(generics.ListAPIView):
    queryset = AppointmentSlot.objects.all()
    serializer_class = SlotSerializer


class RegisterSlot(generics.GenericAPIView):
    queryset = AppointmentSlot.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = ()

    def post(self, request, *args, **kwargs):
        slot = get_object_or_404(self.get_queryset(), id=kwargs.get('slot_id'))
        serializer = AppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        total = 0
        for child_id in serializer.data['children']:
            child = get_object_or_404(Child.objects.all(), id=child_id)
            defaults = {
                'phone_number': serializer.validated_data['phone'],
                'email': serializer.validated_data['email']
            }
            if request.user:
                defaults['family'] = request.user

            appointment, created = Appointment.objects.get_or_create(child=child, slot=slot, defaults=defaults)
            if created:
                total += 1

        return Response(data={'total': total}, status=status.HTTP_201_CREATED)
