# -*- coding:utf-8 -*-
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404

from rest_framework import mixins, generics, status, filters, views
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import list_route
from rest_framework.response import Response

from absences.models import Absence, Session
from activities.models import Activity, Course
from profiles.models import SchoolYear
from registrations.models import Child, ChildActivityLevel, ExtraInfo, Registration
from schools.models import Building, Teacher

from .permissions import (IsAuthenticated, ManagerPermission, FamilyPermission, InstructorPermission,
                          RegistrationOwnerAdminPermission, ChildOrAdminPermission)
from .serializers import (AbsenceSerializer, SetAbsenceSerializer, SessionSerializer, SessionUpdateSerializer,
                          ActivityDetailedSerializer,
                          ChildrenSerializer, CourseSerializer, TeacherSerializer, BuildingSerializer,
                          RegistrationSerializer, ExtraSerializer, ChildActivityLevelSerializer,
                          ChangeCourseSerializer, CourseChangedSerializer,
                          SimpleChildrenSerializer, YearSerializer)


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


class ChildActivityLevelViewSet(viewsets.ModelViewSet):
    model = ChildActivityLevel
    queryset = ChildActivityLevel.objects.all()
    permission_classes = (InstructorPermission,)
    serializer_class = ChildActivityLevelSerializer

    def get_object(self):
        """
        Returns the object the view is displaying.
        You may want to override this if you need to provide non-standard
        queryset lookups.  Eg if objects are referenced using multiple
        keyword arguments in the url conf.
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        if lookup_url_kwarg in self.kwargs:
            filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        else:
            assert 'activity' in self.request.data, 'expected activity id in payload'
            assert 'child' in self.request.data, ('expected child id in payload')
            filter_kwargs = {
                'activity__id': self.request.data['activity'],
                'child__id': self.request.data['child']
            }

        obj = get_object_or_404(queryset, **filter_kwargs)
        # May raise a permission denied
        self.check_object_permissions(self.request, obj)
        return obj

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid() and 'non_field_errors' in serializer.errors:
            # non_field_errors: we are in a duplicate state (a level already exists for same child
            return self.update(request, *args, **kwargs)
        return super(ChildActivityLevelViewSet, self).create(request, *args, **kwargs)


class SessionViewSet(viewsets.ModelViewSet):
    model = Session
    serializer_class = SessionSerializer
    queryset = Session.objects.all()
    permission_classes = (InstructorPermission,)

    def get_serializer_class(self):
        if self.action in ('retrieve', 'list'):
            return SessionSerializer
        return SessionUpdateSerializer

    def perform_create(self, serializer):
        # set all children as present as defauolt value
        session = serializer.save()
        course = Course.objects.get(pk=serializer.data.get('course'))
        for registration in course.participants.all():
            Absence.objects.update_or_create(
                child=registration.child, session=session,
                defaults={
                    'status': Absence.STATUS.present
                }
            )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer_class()(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(SessionSerializer(instance).data)


class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActivityDetailedSerializer
    model = Activity

    def get_queryset(self):
        queryset = Activity.objects.prefetch_related('courses', 'courses__instructors')
        school_year = self.request.query_params.get('year', None)
        if school_year is not None:
            queryset = queryset.filter(courses__schoolyear_min__lte=school_year,
                                       courses__schoolyear_max__gte=school_year,
                                       courses__visible=True).distinct()
        return queryset


class YearViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = YearSerializer
    model = SchoolYear
    queryset = SchoolYear.visible_objects.all()


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseSerializer
    model = Course

    def get_queryset(self):
        return Course.objects.visible().select_related('activity').prefetch_related('participants', 'instructors')


class TeacherViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TeacherSerializer
    model = Teacher

    def get_queryset(self):
        return Teacher.objects.prefetch_related('years')


class BuildingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BuildingSerializer
    model = Building
    queryset = Building.objects.all()


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


class ChildrenViewSet(viewsets.ModelViewSet):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (FamilyPermission, )
    serializer_class = ChildrenSerializer
    model = Child

    def get_queryset(self):
        return Child.objects.filter(Q(family=None) | Q(family=self.request.user))\
                            .prefetch_related('school_year')\
                            .select_related('teacher')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        ext_id = self.request.query_params.get('ext', None)
        if ext_id is not None:
            try:
                ext_id = int(ext_id)
                queryset = queryset.filter(id_lagapeo=ext_id)
            except ValueError:
                queryset = queryset.none()
        else:
            queryset = queryset.filter(family=request.user)
        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        if 'ext_id' in request.data and not request.data['ext_id']:
            del request.data['ext_id']
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.validated_data['family'] = request.user
            if serializer.validated_data.get('school', None) and 'other_school' in serializer.validated_data:
                del serializer.validated_data['other_school']
            try:
                self.object = serializer.save()
            except IntegrityError:
                return Response('Child already exist', status=status.HTTP_400_BAD_REQUEST)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED,
                            headers=headers)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def perform_update(self, serializer):
        serializer.validated_data['family'] = self.request.user
        if 'ext_id' in serializer.validated_data:
            del serializer.validated_data['ext_id']
        if serializer.validated_data.get('school', None):
            serializer.validated_data['other_school'] = ''
        serializer.save()


class SimpleChildrenViewSet(viewsets.ReadOnlyModelViewSet):
    model = Child
    permission_classes = (ManagerPermission, )
    serializer_class = SimpleChildrenSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('first_name', 'last_name')


class RegistrationViewSet(viewsets.ModelViewSet):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (ChildOrAdminPermission, )
    serializer_class = RegistrationSerializer
    model = Registration

    def get_queryset(self):
        user = self.request.user
        return Registration.objects.filter(child__in=user.children.all())

    def create(self, request, *args, **kwargs):
        if type(request.data) is list:
            data = []
            errors = []
            self.get_queryset().exclude(validated=True).exclude(paid=True).delete()
            for registration in request.data:
                serializer = RegistrationSerializer(data=registration)
                if serializer.is_valid():
                    serializer.save()
                    data.append(serializer.data)
                else:
                    errors.append(serializer.errors)
            if data:
                return Response(data, status=status.HTTP_201_CREATED)
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer = RegistrationSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ExtraInfoViewSet(viewsets.ModelViewSet):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (RegistrationOwnerAdminPermission, )
    serializer_class = ExtraSerializer
    model = ExtraInfo

    def get_queryset(self):
        user = self.request.user
        return ExtraInfo.objects.filter(registration__child__in=user.children.all())

    def create(self, request, *args, **kwargs):
        base_data = {'registration': request.data.get('registration', None)}
        output = []
        for (key, value) in request.data.items():
            if key.startswith('extra-') and value:
                data = base_data.copy()
                data['key'] = key.split('-')[1]
                data['value'] = value
                serializer = self.get_serializer(data=data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                output.append(serializer.data)

        return Response(output, status=status.HTTP_201_CREATED)


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
