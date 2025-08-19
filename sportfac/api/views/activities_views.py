from django.conf import settings
from django.core.cache import cache
from django.http import Http404
from rest_framework import mixins
from rest_framework import status
from rest_framework import views
from rest_framework import viewsets
from rest_framework.response import Response

from activities.models import Activity
from activities.models import Course
from activities.models import CoursesInstructors
from registrations.models import Registration

from ..permissions import ManagerPermission
from ..serializers import ActivityDetailedSerializer
from ..serializers import ChangeCourseSerializer
from ..serializers import CourseChangedSerializer
from ..serializers import CourseSerializer
from ..serializers import CoursesInstructorsRoleSerializer


class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActivityDetailedSerializer
    model = Activity

    def get_queryset(self):
        queryset = Activity.objects.prefetch_related("courses", "courses__instructors", "courses__sessions")
        if settings.KEPCHUP_LIMIT_BY_SCHOOL_YEAR:
            school_year = self.request.query_params.get("year")
            if school_year is not None:
                try:
                    queryset = (
                        queryset.exclude(courses__course_type=Course.TYPE.unregistered_course, courses__visible=False)
                        .filter(
                            courses__schoolyear_min__lte=int(school_year),
                            courses__schoolyear_max__gte=int(school_year),
                            courses__visible=True,
                        )
                        .distinct()
                    )
                except ValueError:
                    pass
        else:
            birth_date = self.request.query_params.get("birth_date")
            if birth_date is not None:
                return (
                    queryset.exclude(courses__course_type=Course.TYPE.unregistered_course, courses__visible=False)
                    .filter(
                        courses__min_birth_date__gte=birth_date,
                        courses__max_birth_date__lte=birth_date,
                        courses__visible=True,
                    )
                    .distinct()
                )

        return queryset


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseSerializer
    model = Course

    def get_queryset(self):
        return Course.objects.registerable().select_related("activity").prefetch_related("instructors", "sessions")

    def retrieve(self, request, pk=None):
        tenant_pk = request.tenant.pk
        cache_key = f"tenant_{tenant_pk}_course_{pk}"
        data = cache.get(cache_key)
        if data:
            return Response(data)
        response = super().retrieve(request, pk=pk)
        cache.set(cache_key, response.data)
        return response


class ChangeCourse(views.APIView):
    permission_classes = (ManagerPermission,)
    serializer_class = ChangeCourseSerializer

    def put(self, request, *args, **kwargs):
        serializer = ChangeCourseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            registration = Registration.objects.validated().get(
                child=serializer.validated_data["child"],
                course=serializer.validated_data["previous_course"],
            )
        except Registration.DoesNotExist:
            raise Http404
        new_course = serializer.validated_data["new_course"]
        registration.course = new_course
        registration.save()
        return Response(CourseChangedSerializer(new_course).data, status=status.HTTP_200_OK)


class CourseInstructorsViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = (ManagerPermission,)
    queryset = CoursesInstructors.objects.all()
    serializer_class = CoursesInstructorsRoleSerializer
