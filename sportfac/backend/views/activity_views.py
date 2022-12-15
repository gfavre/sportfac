# -*- coding: utf-8 -*-
from __future__ import absolute_import

import collections
import os
from tempfile import mkdtemp

from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from absences.models import Absence, Session
from absences.utils import closest_session
from activities.forms import ActivityForm
from activities.models import Activity, Course, ExtraNeed
from registrations.models import ChildActivityLevel, ExtraInfo

from ..forms import SessionForm
from ..utils import AbsencePDFRenderer
from .mixins import BackendMixin


__all__ = [
    "ActivityDetailView",
    "ActivityListView",
    "ActivityCreateView",
    "ActivityUpdateView",
    "ActivityDeleteView",
    "ActivityAbsenceView",
]


class ActivityDetailView(BackendMixin, DetailView):
    model = Activity
    slug_field = "slug"
    slug_url_kwarg = "activity"
    template_name = "backend/activity/detail.html"


class ActivityListView(BackendMixin, ListView):
    model = Activity
    template_name = "backend/activity/list.html"


class ActivityCreateView(SuccessMessageMixin, BackendMixin, CreateView):
    model = Activity
    form_class = ActivityForm
    success_url = reverse_lazy("backend:activity-list")
    success_message = _(
        '<a href="%(url)s" class="alert-link">Activity (%(number)s)</a> has been created.'
    )
    template_name = "backend/activity/create.html"

    def get_success_message(self, cleaned_data):
        url = self.object.get_backend_url()
        return mark_safe(self.success_message % {"url": url, "number": self.object.number})


class ActivityAbsenceView(BackendMixin, DetailView):
    model = Activity
    template_name = "backend/activity/absences.html"
    slug_field = "slug"
    slug_url_kwarg = "activity"

    def post(self, *args, **kwargs):
        activity = self.get_object()
        form = SessionForm(data=self.request.POST)
        if form.is_valid():
            msg = []
            with transaction.atomic():
                for course in activity.courses.all():
                    session, created = Session.objects.get_or_create(
                        course=course,
                        date=form.cleaned_data["date"],
                        defaults={"activity": activity},
                    )
                    session.fill_absences()
                    if settings.KEPCHUP_EXPLICIT_SESSION_DATES:
                        session.update_courses_dates()
                    if created:
                        msg.append(
                            _("Session of %(date)s for %(course)s has been added.")
                            % {"date": session.date.strftime("%d.%m.%Y"), "course": course.number}
                        )
            messages.success(self.request, mark_safe("<br>".join(msg)))

        return HttpResponseRedirect(activity.backend_absences_url)

    def get_context_data(self, **kwargs):
        qs = Absence.objects.select_related(
            "child",
            "session",
            "session__course",
        ).filter(session__activity=self.object)
        all_registrations = self.object.participants.select_related("child")
        if "c" in self.request.GET:
            courses_ids = [int(pk) for pk in self.request.GET.getlist("c") if pk.isdigit()]
            if len(courses_ids) == 1:
                try:
                    kwargs["course"] = Course.objects.get(pk=courses_ids[0])
                except Course.DoesNotExist:
                    pass
            all_registrations = all_registrations.filter(course_id__in=courses_ids)
        elif self.object.courses.count() == 1:
            kwargs["course"] = self.object.courses.first()
        if settings.KEPCHUP_BIB_NUMBERS:
            qs = qs.order_by("child__bib_number", "child__last_name", "child__first_name")
        else:
            qs = qs.order_by("child__last_name", "child__first_name")

        if "course" in kwargs:
            sessions = kwargs["course"].sessions.all()
        else:
            sessions = self.object.sessions.all()
        kwargs["sessions"] = dict([(session.date, session) for session in sessions])
        kwargs["closest_session"] = closest_session(sessions)
        # kwargs['sessions'] = dict([(absence.session.date, absence.session) for absence in qs])
        kwargs["all_dates"] = sorted(
            [session_date for session_date in kwargs["sessions"].keys()], reverse=True
        )

        registrations = dict(
            [(registration.child, registration) for registration in all_registrations]
        )
        child_absences = collections.OrderedDict()
        for (child, registration) in sorted(
            list(registrations.items()), key=lambda x: x[0].ordering_name
        ):
            child_absences[(child, registration)] = {}
        for absence in qs:
            child = absence.child
            if not child in registrations:
                # happens if child was previously attending this course but is no longer
                continue
            registration = registrations[child]

            the_tuple = (child, registration)
            if the_tuple in child_absences:
                child_absences[the_tuple][absence.session.date] = absence
            else:
                child_absences[the_tuple] = {absence.session.date: absence}
        kwargs["session_form"] = SessionForm()
        kwargs["child_absences"] = child_absences
        # kwargs['courses_list'] = Course.objects.select_related('activity')
        if settings.KEPCHUP_REGISTRATION_LEVELS:
            kwargs["levels"] = ChildActivityLevel.LEVELS
            kwargs["child_levels"] = dict(
                [
                    (lvl.child, lvl)
                    for lvl in ChildActivityLevel.objects.filter(
                        activity=self.object
                    ).select_related("child")
                ]
            )
            try:
                questions = ExtraNeed.objects.filter(question_label__startswith="Niveau")
                all_extras = dict(
                    [
                        (extra.registration.child, extra.value)
                        for extra in ExtraInfo.objects.filter(
                            registration__course__activity=self.object, key__in=questions
                        ).select_related("registration__child")
                    ]
                )
            except ExtraNeed.DoesNotExist:
                all_extras = {}
            kwargs["extras"] = all_extras
        return super(ActivityAbsenceView, self).get_context_data(**kwargs)

    def get(self, request, *args, **kwargs):
        if "pdf" in self.request.GET:
            self.object = self.get_object()
            context = self.get_context_data(object=self.object)
            renderer = AbsencePDFRenderer(context, self.request)
            tempdir = mkdtemp()
            filename = "absences-{}.pdf".format(slugify(self.object.number))
            filepath = os.path.join(tempdir, filename)
            renderer.render_to_pdf(filepath)
            response = HttpResponse(open(filepath).read(), content_type="application/pdf")
            response["Content-Disposition"] = 'attachment; filename="{}"'.format(filename)
            return response
        return super(ActivityAbsenceView, self).get(request, *args, **kwargs)


class ActivityUpdateView(SuccessMessageMixin, BackendMixin, UpdateView):
    model = Activity
    form_class = ActivityForm
    slug_field = "slug"
    slug_url_kwarg = "activity"
    success_url = reverse_lazy("backend:activity-list")
    success_message = _(
        '<a href="%(url)s" class="alert-link">Activity (%(number)s)</a> has been updated.'
    )
    template_name = "backend/activity/update.html"

    def get_success_message(self, cleaned_data):
        url = self.object.get_backend_url()
        return mark_safe(self.success_message % {"url": url, "number": self.object.number})


class ActivityDeleteView(SuccessMessageMixin, BackendMixin, DeleteView):
    model = Activity
    slug_field = "slug"
    slug_url_kwarg = "activity"
    success_message = _("Activity has been deleted.")
    success_url = reverse_lazy("backend:activity-list")
    template_name = "backend/activity/confirm_delete.html"

    def delete(self, request, *args, **kwargs):
        # noinspection PyAttributeOutsideInit
        self.object = self.get_object()
        identifier = self.get_object().number
        messages.success(
            self.request,
            _("Activity %(identifier)s has been deleted.") % {"identifier": identifier},
        )
        return super(ActivityDeleteView, self).delete(request, *args, **kwargs)
