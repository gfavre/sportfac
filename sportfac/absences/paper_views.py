from datetime import date

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.views import View

from activities.models import Course

from .paper import attendance_workbook
from .paper import next_attendance_date


class PaperAttendanceView(LoginRequiredMixin, View):
    def get(self, request, course):
        if not settings.KEPCHUP_PAPER_ATTENDANCE:
            raise Http404
        course = get_object_or_404(Course.objects.prefetch_related("sessions", "instructors"), pk=course)
        user = request.user
        manages_course = user.is_full_manager or (
            user.is_restricted_manager and user.managed_activities.filter(pk=course.activity_id).exists()
        )
        if not user.is_active or not (manages_course or user.is_instructor_of(course)):
            return HttpResponseForbidden()
        if "date" in request.GET:
            try:
                day = date.fromisoformat(request.GET["date"])
            except ValueError:
                return HttpResponseBadRequest("Date attendue au format AAAA-MM-JJ.")
            if day not in course.all_dates:
                return HttpResponseBadRequest("Cette date ne correspond pas à une séance du cours.")
        else:
            day = next_attendance_date(course)
        if day is None:
            return HttpResponseBadRequest("Aucune séance à venir pour ce cours.")
        response = HttpResponse(
            attendance_workbook(course, day),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="absences-cours-{course.pk}-{day.isoformat()}.xlsx"'
        return response
