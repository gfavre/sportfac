# -*- coding: utf-8 -*-
from __future__ import absolute_import
from django.conf import settings

from rest_framework import status, viewsets
from rest_framework.decorators import list_route
from rest_framework.response import Response

from absences.models import Absence, Session
from registrations.models import Child
from ..permissions import InstructorPermission
from ..serializers import AbsenceSerializer, SetAbsenceSerializer, SessionSerializer, SessionUpdateSerializer


class AbsenceViewSet(viewsets.ModelViewSet):
    model = Absence
    queryset = Absence.objects.all()
    permission_classes = (InstructorPermission,)
    serializer_class = AbsenceSerializer

    @list_route(methods=['post'])
    def set(self, request):
        serializer = SetAbsenceSerializer(data=request.data)
        if serializer.is_valid():
            res_status = serializer.data['status']
            Absence.objects.update_or_create(
                session=Session.objects.get(pk=serializer.data['session']),
                child=Child.objects.get(pk=serializer.data['child']),
                defaults={
                    'status': res_status
                }
            )
            return Response({'status': res_status})
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)


class SessionViewSet(viewsets.ModelViewSet):
    model = Session
    serializer_class = SessionSerializer
    queryset = Session.objects.all()
    permission_classes = (InstructorPermission, )

    def get_serializer_class(self):
        if self.action in ('retrieve', 'list'):
            return SessionSerializer
        return SessionUpdateSerializer

    def perform_create(self, serializer):
        # set all children as present as default value
        session = serializer.save()
        session.fill_absences()
        if settings.KEPCHUP_EXPLICIT_SESSION_DATES:
            session.update_courses_dates()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer_class()(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        if settings.KEPCHUP_EXPLICIT_SESSION_DATES:
            instance.update_courses_dates()
        return Response(SessionSerializer(instance).data)

    def perform_destroy(self, instance):
        if settings.KEPCHUP_ABSENCES_RELATE_TO_ACTIVITIES:
            activity = instance.activity
            sister_sessions = instance.activity.sessions.filter(date=instance.date)
            for session in sister_sessions:
                session.delete()
            if settings.KEPCHUP_EXPLICIT_SESSION_DATES:
                for course in activity.courses.all():
                    course.update_dates_from_sessions()
        else:
            course = instance.course
            instance.delete()
            if settings.KEPCHUP_EXPLICIT_SESSION_DATES:
                course.update_dates_from_sessions()