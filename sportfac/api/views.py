# Create your views here.
from django.http import Http404

from rest_framework import viewsets
from rest_framework.response import Response



from activities.models import Activity
from .serializers import ActivitySerializer, ActivityDetailedSerializer


class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Activity.objects.all()
    serializer_class = ActivityDetailedSerializer
    
    def list(self, request):
        activities = self.get_queryset()
        serializer = ActivitySerializer(activities)
        return Response(serializer.data)