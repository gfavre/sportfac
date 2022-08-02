from rest_framework import status
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response

from profiles.models import SchoolYear
from registrations.models import ExtraInfo, Registration
from schools.models import Building, Teacher

from ..permissions import RegistrationOwnerAdminPermission, ChildOrAdminPermission
from ..serializers import (BuildingSerializer, ExtraSerializer, RegistrationSerializer, TeacherSerializer,
                           YearSerializer)

from waiting_slots.models import WaitingSlot


class WaitingSlotViewSet(viewsets.ModelViewSet):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (ChildOrAdminPermission,)
    serializer_class = RegistrationSerializer
    model = WaitingSlot

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return WaitingSlot.objects.all()
        return WaitingSlot.objects.filter(child__in=user.children.all())
