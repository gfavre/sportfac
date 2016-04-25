# Create your views here.
from django.http import Http404

from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from rest_framework import mixins, generics, status, filters


from activities.models import Activity, Course
from profiles.models import Child, Teacher, Registration, ExtraInfo
from .serializers import (ActivitySerializer, ActivityDetailedSerializer, 
                          ChildrenSerializer, CourseSerializer, TeacherSerializer,
                          RegistrationSerializer, ExtraSerializer, SimpleChildrenSerializer)


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


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseSerializer
    model = Course
    
    def get_queryset(self):
        return Course.objects.select_related('activity', 'responsible').prefetch_related('participants')
    

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


class ManagerPermission(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.user.is_manager:
            return True
        return False


class FamilyOrAdminPermission(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.user.is_manager or request.user == obj.family:
            return True
        return False


class ChildrenViewSet(viewsets.ModelViewSet):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (FamilyOrAdminPermission, )
    serializer_class = ChildrenSerializer
    model = Child        
    
    def get_queryset(self):
        user = self.request.user
        return Child.objects.filter(family=user).prefetch_related('school_year').select_related('teacher')
        
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.validated_data['family'] = request.user
            self.object = serializer.save()
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED,
                            headers=headers)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
        if type(request.DATA) is list:
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