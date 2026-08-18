from django.conf import settings
from django.core.cache import cache
from django.db.models import Prefetch
from django.db.models import Q
from django.http import Http404
from rest_framework import mixins
from rest_framework import status
from rest_framework import views
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from activities.cache import get_structural_activities_cache_key
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


# Safety net only: real edits invalidate this cache immediately via
# activities.signals, this timeout just bounds the damage from any edit path that
# doesn't go through Model.save() (bulk_update, raw SQL, admin bulk actions...).
ACTIVITIES_STRUCTURAL_CACHE_TIMEOUT = 120  # seconds


class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActivityDetailedSerializer
    model = Activity

    def get_queryset(self):
        valid_courses = Course.objects.exclude(course_type=Course.TYPE.unregistered_course).filter(visible=True)

        if settings.KEPCHUP_LIMIT_BY_SCHOOL_YEAR:
            school_year = self.request.query_params.get("year")
            if school_year is not None:
                try:
                    school_year = int(school_year)
                    valid_courses = valid_courses.filter(
                        Q(schoolyear_min__isnull=True)
                        | Q(schoolyear_min__lte=school_year, schoolyear_max__gte=school_year)
                    )
                except ValueError:
                    pass
        else:
            birth_date = self.request.query_params.get("birth_date")
            if birth_date is not None:
                valid_courses = valid_courses.filter(
                    # "no restriction" is decided from age_min/age_max (the field staff
                    # actually edit) rather than min_birth_date/max_birth_date (a derived
                    # cache that can go stale independently - see Course.save()) - once
                    # there is a restriction, the derived dates are accurate and fine to
                    # use for the actual range comparison below.
                    Q(age_min__isnull=True, age_max__isnull=True)
                    | Q(min_birth_date__gte=birth_date, max_birth_date__lte=birth_date)
                )

        # 🔑 On sélectionne uniquement les activités qui ont AU MOINS un cours valide
        queryset = (
            Activity.objects.filter(courses__in=valid_courses)
            .distinct()
            .prefetch_related(
                Prefetch(
                    "courses",
                    queryset=valid_courses.prefetch_related("instructors", "sessions"),
                )
            )
        )

        return queryset  # noqa: R504

    def _get_structural_activities(self):
        """All visible, registerable activities/courses, unfiltered by any family's eligibility.

        This payload is identical for every family regardless of which child they're looking at,
        so it's cached per-tenant (not per query param) and shared across every concurrent
        request - unlike a cache keyed by (year, birth_date), which would essentially never hit
        since each child has a different birth date. Eligibility filtering happens afterwards, in
        Python, against this shared cache (see list()).

        Deliberately contains no participant-count/fullness data (CourseInlineSerializer doesn't
        expose it - that only shows up in the per-course detail modal, via CourseViewSet.retrieve,
        which is already cached and already correctly invalidated on every registration). So this
        cache never needs to react to registrations, which is what makes a shared cache safe here
        during a rush: only real course/activity edits invalidate it, via
        activities.signals.invalidate_activities_structural_cache (which explicitly ignores
        nb_participants-only saves so registrations don't churn it).
        """
        tenant_pk = self.request.tenant.pk
        cache_key = get_structural_activities_cache_key(tenant_pk)
        data = cache.get(cache_key)
        if data is None:
            valid_courses = Course.objects.exclude(course_type=Course.TYPE.unregistered_course).filter(visible=True)
            queryset = (
                Activity.objects.filter(courses__in=valid_courses)
                .distinct()
                .prefetch_related(
                    Prefetch("courses", queryset=valid_courses.prefetch_related("instructors", "sessions"))
                )
            )
            data = ActivityDetailedSerializer(queryset, many=True).data
            cache.set(cache_key, data, ACTIVITIES_STRUCTURAL_CACHE_TIMEOUT)
        return data

    @staticmethod
    def _course_matches_school_year(course, school_year):
        if not course["has_school_year_restriction"]:
            # No school-year restriction on this course (mirrors _course_matches_birth_date) -
            # without this check, comparing None to an int raises TypeError in Python, which
            # crashed this whole request and silently hid every course from the activity, not
            # just the unrestricted one.
            return True
        return course["schoolyear_min"] <= school_year <= course["schoolyear_max"]

    @staticmethod
    def _course_matches_birth_date(course, birth_date):
        # has_age_restriction (live-computed from age_min/age_max) rather than
        # min_birth_date being None: min_birth_date/max_birth_date are a derived cache
        # that can go stale independently of age_min/age_max (see Course.save()) - a
        # course edited to remove its age restriction must stop being excluded
        # immediately, not only after its next unrelated save().
        if not course["has_age_restriction"]:
            return True
        return course["min_birth_date"] >= birth_date and course["max_birth_date"] <= birth_date

    @staticmethod
    def _filter_activities(activities, course_matches):
        filtered = []
        for activity in activities:
            courses = [course for course in activity["courses"] if course_matches(course)]
            if courses:
                filtered.append({**activity, "courses": courses})
        return filtered

    def list(self, request, *args, **kwargs):
        activities = self._get_structural_activities()

        if settings.KEPCHUP_LIMIT_BY_SCHOOL_YEAR:
            school_year = request.query_params.get("year")
            if school_year is not None:
                try:
                    school_year = int(school_year)
                except ValueError:
                    school_year = None
                if school_year is not None:
                    activities = self._filter_activities(
                        activities, lambda course: self._course_matches_school_year(course, school_year)
                    )
        else:
            birth_date = request.query_params.get("birth_date")
            if birth_date is not None:
                activities = self._filter_activities(
                    activities, lambda course: self._course_matches_birth_date(course, birth_date)
                )

        return Response(activities)


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

    MAX_BATCH_IDS = 200

    @action(detail=False, methods=["get"])
    def batch(self, request):
        """Same per-course cache as retrieve(), fetched for several ids in one request -
        lets the activities-step SPA replace its one-request-per-visible-course polling
        with a single call without losing per-course cache granularity/invalidation."""
        try:
            ids = [int(i) for i in request.query_params.get("ids", "").split(",") if i]
        except ValueError:
            return Response({"ids": "Must be a comma-separated list of integers."}, status=status.HTTP_400_BAD_REQUEST)
        if not ids:
            return Response([])
        if len(ids) > self.MAX_BATCH_IDS:
            return Response(
                {"ids": f"Too many ids: {len(ids)} (max {self.MAX_BATCH_IDS})."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tenant_pk = request.tenant.pk
        cache_keys_by_id = {course_id: f"tenant_{tenant_pk}_course_{course_id}" for course_id in ids}
        cached = cache.get_many(cache_keys_by_id.values())

        data_by_id = {
            course_id: cached[cache_key] for course_id, cache_key in cache_keys_by_id.items() if cache_key in cached
        }
        missing_ids = [course_id for course_id in ids if course_id not in data_by_id]
        if missing_ids:
            serializer = self.get_serializer(self.get_queryset().filter(id__in=missing_ids), many=True)
            to_cache = {}
            for item in serializer.data:
                data_by_id[item["id"]] = item
                to_cache[cache_keys_by_id[item["id"]]] = item
            cache.set_many(to_cache)

        # ids without a match (deleted, or no longer registerable) are silently dropped,
        # same as a 404 would be for a single retrieve() of a stale id.
        return Response([data_by_id[course_id] for course_id in ids if course_id in data_by_id])


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

    def partial_update(self, request, *args, **kwargs):
        """
        Allow partial updates of course instructor fields.
        Only provided fields are validated and updated.
        """
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)
