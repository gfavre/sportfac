# Create your views here.
from django.http import Http404

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework import mixins, generics

from activities.models import Activity, Course
from profiles.models import Child
from .serializers import (ActivitySerializer, ActivityDetailedSerializer, 
                          ChildrenSerializer, CourseSerializer)


class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActivityDetailedSerializer
    model = Activity
    
    def get_queryset(self):
        queryset = Activity.objects.all()
        school_year = self.request.QUERY_PARAMS.get('year', None)
        if school_year is not None:
            queryset = queryset.filter(courses__schoolyear_min__lte=school_year,
                                       courses__schoolyear_max__gte=school_year).distinct()
        return queryset
    
    def list(self, request):
        activities = self.get_queryset()
        serializer = ActivitySerializer(activities)
        return Response(serializer.data)


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseSerializer
    model = Course


class FamilyView(mixins.ListModelMixin, generics.GenericAPIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = ChildrenSerializer
    model = Child
    
    def get_queryset(self):
        user = self.request.user
        return Child.objects.filter(family=user)
    
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)
        