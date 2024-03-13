import json
import time
from collections import OrderedDict
from datetime import datetime, timedelta

from django.contrib import messages
from django.db import models
from django.db.models import Count, Func, Max, Sum
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.views.generic import FormView, TemplateView

from activities.models import Activity, Course
from backend.forms import RegistrationDatesForm
from profiles.models import City, FamilyUser, SchoolYear
from registrations.models import Bill, Registration
from schools.models import Teacher

from .mixins import BackendMixin, FullBackendMixin


###############################################################################
# Homepage


class Year(Func):
    function = "EXTRACT"
    template = "%(function)s(YEAR from %(expressions)s)"
    output_field = models.IntegerField()


class Month(Func):
    function = "EXTRACT"
    template = "%(function)s(MONTH from %(expressions)s)"
    output_field = models.IntegerField()


class HomePageView(BackendMixin, TemplateView):
    def get_template_names(self):
        return "backend/dashboard-phase%i.html" % self.request.PHASE

    def get_additional_context_phase1(self, context):
        # noinspection PyUnresolvedReferences
        context["nb_teachers"] = Teacher.objects.count()
        context["last_teacher_update"] = Teacher.objects.aggregate(latest=Max("modified"))["latest"] or "n/a"
        years = SchoolYear.visible_objects.annotate(num_teachers=(Count("teacher"))).filter(num_teachers__gt=0)
        context["teachers_per_year"] = [(year.get_year_display(), year.num_teachers) for year in years]

        activities = context["activities"]
        instructors = context["instructors"]
        courses = context["courses"]

        context["nb_activities"] = activities.count()
        context["nb_courses"] = courses.count()
        context["ready_courses"] = courses.filter(uptodate=True).count()
        context["notready_courses"] = context["nb_courses"] - context["ready_courses"]
        context["total_sessions"] = list(courses.aggregate(Sum("number_of_sessions")).values())[0] or 0
        context["last_course_update"] = courses.aggregate(latest=Max("modified"))["latest"] or "n/a"

        context["total_instructors"] = instructors.count()
        return self._add_cities_context(context)

    def _get_registrations_qs(self):
        # noinspection PyUnresolvedReferences
        user: FamilyUser = self.request.user
        if user.is_restricted_manager:
            return Registration.objects.filter(course__activity__in=user.managed_activities.all())
        return Registration.objects.all()

    def _get_registrations_per_day(self):
        # noinspection PyUnresolvedReferences
        total_per_day = {}
        start = self.request.tenant.preferences["phase__START_REGISTRATION"]
        end = self.request.tenant.preferences["phase__END_REGISTRATION"]
        registrations_qs = self._get_registrations_qs().filter(created__range=(start, end))

        registrations = [d.date() for d in registrations_qs.values_list("created", flat=True)]

        for date in registrations:
            milliseconds = int(time.mktime(date.timetuple()) * 1000)
            total_per_day.setdefault(milliseconds, 0)
            total_per_day[milliseconds] += 1

        return [[k, total_per_day[k]] for k in sorted(total_per_day)]

    def _get_registrations_per_month(self):
        start = self.request.tenant.preferences["phase__START_REGISTRATION"]
        end = self.request.tenant.preferences["phase__END_REGISTRATION"]
        registrations_qs = self._get_registrations_qs()
        registrations = (
            registrations_qs.filter(created__range=(start, end))
            .order_by("created")
            .annotate(year=Year("created"), month=Month("created"))
            .order_by("year", "month")
            .values("year", "month")
            .annotate(total=Count("*"))
            .values("year", "month", "total")
        )
        from django.template.defaultfilters import date as _date

        return OrderedDict(
            (_date(datetime(reg["year"], reg["month"], 1), "b Y"), reg["total"]) for reg in registrations
        )

    def get_additional_context_phase2(self, context):
        registrations_qs = self._get_registrations_qs()
        waiting = set(
            registrations_qs.filter(status=Registration.STATUS.waiting)
            .select_related("child__family")
            .values_list("child__family")
        )
        valid = set(
            registrations_qs.filter(status=Registration.STATUS.valid)
            .select_related("child__family")
            .values_list("child__family")
        )
        context["waiting"] = len(waiting)
        context["valid"] = len(valid)

        # noinspection PyUnresolvedReferences
        context["payement_due"] = Bill.waiting.filter(total__gt=0).count()
        # noinspection PyUnresolvedReferences
        context["paid"] = Bill.paid.filter(total__gt=0).count()
        courses = context["courses"]
        participants = courses.annotate(count_participants=Count("participants")).values_list(
            "min_participants", "max_participants", "count_participants"
        )
        context["nb_full_courses"] = 0
        context["nb_minimal_courses"] = 0

        for min_participants, max_participants, count_participants in participants:
            if min_participants <= count_participants:
                context["nb_minimal_courses"] += 1
                if max_participants == count_participants:
                    context["nb_full_courses"] += 1

        context = self._add_cities_context(context)
        context = self._add_registrations_context(context)

        return context

    def get_additional_context_phase3(self, context):
        courses = context["courses"]
        participants = courses.annotate(count_participants=Count("participants")).values_list(
            "min_participants", "max_participants", "count_participants"
        )
        context["nb_courses"] = len(participants)
        context["nb_full_courses"] = 0
        context["nb_minimal_courses"] = 0
        registrations_qs = self._get_registrations_qs()
        waiting = set(
            registrations_qs.filter(status=Registration.STATUS.waiting)
            .select_related("child__family")
            .values_list("child__family")
        )
        valid = set(
            registrations_qs.filter(status=Registration.STATUS.valid)
            .select_related("child__family")
            .values_list("child__family")
        )
        context["waiting"] = len(waiting)
        context["valid"] = len(valid)
        for min_participants, max_participants, count_participants in participants:
            if min_participants <= count_participants:
                context["nb_minimal_courses"] += 1
                if max_participants == count_participants:
                    context["nb_full_courses"] += 1

        context["payement_due"] = Bill.waiting.count()
        paid = Bill.paid.all()
        context["paid"] = paid.count()
        context["total_due"] = list(Bill.objects.aggregate(Sum("total")).values())[0] or 0
        context["total_paid"] = list(paid.aggregate(Sum("total")).values())[0] or 0
        context = self._add_cities_context(context)
        context = self._add_registrations_context(context)
        return context

    def _add_cities_context(self, context):
        reg_qs = self._get_registrations_qs()
        qs = reg_qs.exclude(status__in=(Registration.STATUS.canceled, Registration.STATUS.waiting)).select_related(
            "child", "child__family"
        )

        context["nb_registrations"] = reg_qs.count()
        children = {reg.child for reg in qs}
        families = {child.family for child in children}
        context["nb_families"] = len(families)
        context["nb_children"] = len(children)

        UNKNOWN = _("Unknown")
        children_per_zip = {UNKNOWN: set()}
        families_per_zip = {UNKNOWN: set()}

        cities = dict(
            City.objects.filter(zipcode__in=qs.values_list("child__family__zipcode").distinct()).values_list(
                "zipcode", "name"
            )
        )
        for zipcode, _city in cities.items():
            children_per_zip[zipcode] = set()
            families_per_zip[zipcode] = set()

        for registration in qs:
            try:
                zipcode = registration.child.family.zipcode
            except AttributeError:
                continue
            if zipcode not in cities:
                zipcode = UNKNOWN
            children_per_zip[zipcode].add(registration.child)
            families_per_zip[zipcode].add(registration.child.family)

        children_per_zip_ordered = sorted(
            [(zipcode, len(children)) for (zipcode, children) in children_per_zip.items()],
            key=lambda x: x[1],
        )

        context["children_per_zip_labels"] = json.dumps(
            ["{} {}".format(zipcode, cities.get(zipcode, "")).strip() for zipcode, nb in children_per_zip_ordered]
        )
        context["children_per_zip_data"] = json.dumps([nb for zipcode, nb in children_per_zip_ordered])

        families_per_zip_ordered = sorted(
            [(zipcode, len(families)) for (zipcode, families) in families_per_zip.items()],
            key=lambda x: x[1],
        )
        context["families_per_zip_labels"] = json.dumps(
            ["{} {}".format(zipcode, cities.get(zipcode, "")).strip() for zipcode, nb in families_per_zip_ordered]
        )
        context["families_per_zip_data"] = json.dumps([nb for zipcode, nb in families_per_zip_ordered])

        return context

    def _add_registrations_context(self, context):
        start = self.request.tenant.preferences["phase__START_REGISTRATION"]
        end = self.request.tenant.preferences["phase__END_REGISTRATION"]
        if (end - start).days > 45:
            context["registrations_period"] = "monthly"
            registrations = self._get_registrations_per_month()
            context["monthly_registrations_labels"] = json.dumps(list(registrations.keys()))
            context["monthly_registrations_data"] = json.dumps(list(registrations.values()))
        else:
            context["registrations_period"] = "daily"
            context["registrations_per_day"] = self._get_registrations_per_day()
        return context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["now"] = now()
        # noinspection PyUnresolvedReferences
        user: FamilyUser = self.request.user
        if user.is_full_manager:
            activities = Activity.objects.all()
            courses = Course.objects.all()
            instructors = FamilyUser.instructors_objects.all()
        else:
            activities = user.managed_activities.all()
            courses = Course.objects.filter(activity__in=activities)
            instructors = FamilyUser.instructors_objects.filter(coursesinstructors__course__activity__in=activities)

        context["courses"] = courses
        context["activities"] = activities
        context["instructors"] = instructors

        context["nb_courses"] = courses.count()
        context["nb_activities"] = activities.count()

        context["total_sessions"] = list(courses.aggregate(Sum("number_of_sessions")).values())[0] or 0
        context["total_instructors"] = instructors.count()

        timedeltas = []
        for course in courses:
            if not course.is_camp:
                timedeltas.append(course.number_of_sessions * course.duration)
        td = sum(timedeltas, timedelta())
        context["total_hours"] = int(td.days * 24 + td.seconds / 3600)
        context["total_remaining_minutes"] = int((td.seconds % 3600) / 60)

        method_name = "get_additional_context_phase%i" % self.request.PHASE
        return getattr(self, method_name)(context)


###############################################################################
# Dates
class RegistrationDatesView(FullBackendMixin, FormView):
    template_name = "backend/registration_dates.html"
    form_class = RegistrationDatesForm
    success_url = reverse_lazy("backend:home")

    def get_initial(self):
        initial = super().get_initial()
        initial["opening_date"] = self.request.tenant.preferences["phase__START_REGISTRATION"]
        initial["closing_date"] = self.request.tenant.preferences["phase__END_REGISTRATION"]
        return initial

    def form_valid(self, form):
        self.request.tenant.preferences["phase__START_REGISTRATION"] = form.cleaned_data["opening_date"]
        self.request.tenant.preferences["phase__END_REGISTRATION"] = form.cleaned_data["closing_date"]
        messages.add_message(self.request, messages.SUCCESS, _("Opening and closing dates have been changed"))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.add_message(
            self.request,
            messages.ERROR,
            mark_safe(_("An error was found in form %s") % form.non_field_errors()),
        )
        return super().form_invalid(form)
