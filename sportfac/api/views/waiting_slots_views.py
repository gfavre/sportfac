from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from waiting_slots.models import WaitingSlot

from ..permissions import ChildOrAdminPermission
from ..serializers import WaitingSlotSerializer


class WaitingSlotViewSet(viewsets.ModelViewSet):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (ChildOrAdminPermission,)
    serializer_class = WaitingSlotSerializer
    model = WaitingSlot

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return WaitingSlot.objects.all()
        return WaitingSlot.objects.filter(child__in=user.children.all())
