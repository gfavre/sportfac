# -*- coding: utf-8 -*-
from django.http import Http404

from rest_framework import status, views, viewsets
from rest_framework.response import Response

from activities.models import Activity, Course
from registrations.models import Registration
from ..permissions import ManagerPermission
from ..serializers import (ActivityDetailedSerializer, CourseSerializer, ChangeCourseSerializer,
                           CourseChangedSerializer)


class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActivityDetailedSerializer
    model = Activity

    def get_queryset(self):
        queryset = Activity.objects.prefetch_related('courses', 'courses__instructors')
        school_year = int(self.request.query_params.get('year', None))
        if school_year is not None:
            try:
                queryset = queryset.filter(courses__schoolyear_min__lte=int(school_year),
                                           courses__schoolyear_max__gte=int(school_year),
                                           courses__visible=True).distinct()
            except ValueError:
                pass
        return queryset


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseSerializer
    model = Course

    def get_queryset(self):
        return Course.objects.visible().select_related('activity').prefetch_related('participants', 'instructors')


class ChangeCourse(views.APIView):
    permission_classes = (ManagerPermission,)
    serializer_class = ChangeCourseSerializer

    def put(self, request, *args, **kwargs):
        serializer = ChangeCourseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            registration = Registration.objects.validated().get(child=serializer.validated_data['child'],
                                                                course=serializer.validated_data['previous_course'])
        except Registration.DoesNotExist:
            raise Http404
        new_course = serializer.validated_data['new_course']
        registration.course = new_course
        registration.save()
        return Response(CourseChangedSerializer(new_course).data, status=status.HTTP_200_OK)
