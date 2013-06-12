# Create your views here.
from django.http import Http404

from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from rest_framework import mixins, generics, status



from activities.models import Activity, Course
from profiles.models import Child, Teacher
from .serializers import (ActivitySerializer, ActivityDetailedSerializer, 
                          ChildrenSerializer, CourseSerializer, TeacherSerializer)


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
    
    def get_queryset(self):
        return Course.objects.select_related('activity', 'responsible')

    

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


class FamilyOrAdminPermission(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.user.is_staff or request.user == obj.family:
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
        serializer = self.get_serializer(data=request.DATA, files=request.FILES)
        if serializer.is_valid():
            serializer.object.family = request.user
            self.object = serializer.save(force_insert=True)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED,
                            headers=headers)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    
    
    
        