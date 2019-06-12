# -*- coding: utf-8 -*-
import collections
import os
from tempfile import mkdtemp

from django.conf import settings
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponse
from django.views.generic import DetailView

from activities.views import InstructorMixin
from activities.models import Activity, Course, ExtraNeed
from backend.forms import SessionForm  # TODO move sessionform to a more appropriate place
from backend.utils import AbsencePDFRenderer  # TODO move pdfrenderer to a more appropriate place

from registrations.models import ChildActivityLevel, ExtraInfo
from .models import Absence, Session


class AbsenceCourseView(InstructorMixin, DetailView):
    template_name = 'absences/absences.html'
    pk_url_kwarg = 'course'

    def get_queryset(self):
        return Course.objects.prefetch_related('sessions', 'sessions__absences', 'participants__child')

    def get_context_data(self, **kwargs):
        course = self.get_object()
        qs = Absence.objects.select_related('child', 'session').filter(session__course=self.object).order_by('child')
        if settings.KEPCHUP_BIB_NUMBERS:
            qs = qs.order_by('child__bib_number', 'child__last_name', 'child__first_name')
        else:
            qs = qs.order_by('child__last_name', 'child__first_name')
        kwargs['sessions'] = dict([(session.date, session) for session in self.object.sessions.all()])
        # kwargs['sessions'] = dict([(absence.session.date, absence.session) for absence in qs])
        kwargs['all_dates'] = sorted([session_date for session_date in kwargs['sessions'].keys()], reverse=True)

        registrations = dict([(registration.child, registration) for registration in self.object.participants.all()])
        child_absences = collections.OrderedDict()
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
        kwargs['session_form'] = SessionForm()
        kwargs['child_absences'] = child_absences
        if settings.KEPCHUP_REGISTRATION_LEVELS:
            kwargs['levels'] = ChildActivityLevel.LEVELS
            kwargs['child_levels'] = dict(
                [(lvl.child, lvl) for lvl in ChildActivityLevel.objects.filter(activity=self.object.activity)
                                                                       .select_related('child')]
            )
            try:
                question = ExtraNeed.objects.get(question_label__startswith=u'Niveau')
                all_extras = dict(
                    [(extra.registration.child, extra.value) for extra in
                     ExtraInfo.objects.filter(registration__course=self.object, key=question)
                                      .select_related('registration__child')]
                )
            except ExtraNeed.DoesNotExist:
                all_extras = {}
            kwargs['extras'] = all_extras

        kwargs['courses_list'] = self.request.user.course.prefetch_related('activity')
        kwargs['session_form'] = SessionForm()

        return super(AbsenceCourseView, self).get_context_data(**kwargs)

    def post(self, *args, **kwargs):
        course = self.get_object()
        form = SessionForm(data=self.request.POST)
        if form.is_valid():
            with transaction.atomic():
                session, created = Session.objects.get_or_create(course=course,
                                                                 date=form.cleaned_data['date'],
                                                                 defaults={
                                                                     'instructor': self.request.user,
                                                                     'activity': course.activity
                                                                 })
                for registration in course.participants.all():
                    Absence.objects.get_or_create(
                        child=registration.child, session=session,
                        defaults={
                            'status': Absence.STATUS.present
                        }
                    )
        return HttpResponseRedirect(course.get_absences_url())

    def get(self, request, *args, **kwargs):
        if 'pdf' in self.request.GET:
            self.object = self.get_object()
            context = self.get_context_data(object=self.object)
            renderer = AbsencePDFRenderer(context, self.request)
            tempdir = mkdtemp()
            filename = u'absences-{}.pdf'.format(self.object.number)
            filepath = os.path.join(tempdir, filename)
            renderer.render_to_pdf(filepath)
            response = HttpResponse(open(filepath).read(), content_type='application/pdf')
            response['Content-Disposition'] = u'attachment; filename="{}"'.format(filename)
            return response
        return super(AbsenceCourseView, self).get(request, *args, **kwargs)
