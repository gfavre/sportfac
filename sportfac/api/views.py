# Create your views here.
from django.db.models import Q
from django.http import Http404

from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, list_route
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from rest_framework import mixins, generics, status, filters


from absences.models import Absence, Session
from activities.models import Activity, Course
from registrations.models import Child, ExtraInfo, Registration
from profiles.models import SchoolYear
from schools.models import Teacher
from .permissions import ManagerPermission, FamilyOrAdminPermission, FamilyPermission, ResponsiblePermission
from .serializers import (AbsenceSerializer, SetAbsenceSerializer, SessionSerializer,
                          ActivitySerializer, ActivityDetailedSerializer, 
                          ChildrenSerializer, CourseSerializer, TeacherSerializer,
                          RegistrationSerializer, ExtraSerializer, SimpleChildrenSerializer,
                          YearSerializer)


class AbsenceViewSet(viewsets.ModelViewSet):
    model = Absence
    queryset = Absence.objects.all()
    permission_classes = (ResponsiblePermission,)
    serializer_class = AbsenceSerializer
    
    @list_route(methods=['post'])
    def set(self, request):
        serializer = SetAbsenceSerializer(data=request.data)
        if serializer.is_valid():
            status = serializer.data['status']
            obj, created = Absence.objects.get_or_create(
                session=Session.objects.get(pk=serializer.data['session']), 
                child=Child.objects.get(pk=serializer.data['child'])
            )
            if status == 'present':
                self.perform_destroy(obj)
            else:
                obj.status = status
                obj.save()
            return Response({'status': status}) 
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST) 
    


class SessionViewSet(viewsets.ModelViewSet):
    model = Session
    serializer_class = SessionSerializer
    queryset = Session.objects.all()
    permission_classes = (ResponsiblePermission,)
    


class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActivityDetailedSerializer
    model = Activity
    
    def get_queryset(self):
        queryset = Activity.objects.prefetch_related('courses', 'courses__responsible')
        school_year = self.request.query_params.get('year', None)
        if school_year is not None:
            queryset = queryset.filter(courses__schoolyear_min__lte=school_year,
                                       courses__schoolyear_max__gte=school_year).distinct()
        return queryset


class YearViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = YearSerializer
    model = SchoolYear
    queryset = SchoolYear.objects.all()


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseSerializer
    model = Course
    
    def get_queryset(self):
        return Course.objects.visible().select_related('activity', 'responsible').prefetch_related('participants')
    

class TeacherViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TeacherSerializer
    model = Teacher
    
    def get_queryset(self):
        return Teacher.objects.prefetch_related('years')


class FamilyView(mixins.ListModelMixin, generics.GenericAPIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
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
            except:
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
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.validated_data['family'] = request.user
            if serializer.validated_data.get('school', None) and 'other_school' in serializer.validated_data:
                del serializer.validated_data['other_school']
            self.object = serializer.save()
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


class ChildOrAdminPermission(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.user.is_manager or request.user == obj.child.family:
            return True
        return False


class RegistrationViewSet(viewsets.ModelViewSet):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (ChildOrAdminPermission, )
    serializer_class = RegistrationSerializer
    model = Registration
    
    def get_queryset(self):
        user = self.request.user
        return Registration.objects.filter(child__in=user.children.all())
    
    def create(self, request, format=None):
        if type(request.data) is list:
            data = []
            self.get_queryset().exclude(validated=True).exclude(paid=True).delete()
            for registration in request.data:
                serializer = RegistrationSerializer(data=registration)
                if serializer.is_valid():
                    serializer.save()
                    data.append(serializer.data)
            if data:
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer = RegistrationSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class RegistrationOwnerAdminPermission(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.user.is_manager or request.user == obj.registration.child.family:
            return True
        return False


class ExtraInfoViewSet(viewsets.ModelViewSet):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (RegistrationOwnerAdminPermission, )
    serializer_class = ExtraSerializer
    model = ExtraInfo
    
    def get_queryset(self):
        user = self.request.user
        return ExtraInfo.objects.filter(registration__child__in=user.children.all())