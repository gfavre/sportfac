# -*- coding: utf-8 -*-
from django.http import HttpResponseRedirect
from django.views.generic import DetailView

from activities.views import InstructorMixin
from activities.models import Course
from backend.forms import SessionForm  # TODO move sessionform to a more appropriate place
from registrations.models import ChildActivityLevel
from .models import Absence, Session


class AbsenceView(InstructorMixin, DetailView):
    model = Course
    template_name = 'absences/absences.html'
    pk_url_kwarg = 'course'
    queryset = Course.objects.prefetch_related('sessions', 'sessions__absences', 'participants__child')

    def get_context_data(self, **kwargs):
        course = self.get_object()
        all_absences = dict(
            [((absence.child, absence.session), absence.status) for absence
                                                                in Absence.objects.filter(session__course=course)]
        )
        kwargs['absence_matrix'] = [[all_absences.get((registration.child, session), 'present') for session
                                                                     in course.sessions.all()]
         for registration in course.participants.all()]
        kwargs['levels'] = ChildActivityLevel.LEVELS
        kwargs['courses_list'] = self.request.user.course.all()
        kwargs['session_form'] = SessionForm()

        return super(AbsenceView, self).get_context_data(**kwargs)

    def post(self, *args, **kwargs):
        course = self.get_object()
        form = SessionForm(data=self.request.POST)
        if form.is_valid():
            session, created = Session.objects.get_or_create(instructor=self.request.user,
                                                             course=course,
                                                             date=form.cleaned_data['date'])
            for registration in course.participants.all():
                Absence.objects.get_or_create(
                    child=registration.child, session=session,
                    defaults={
                        'status': Absence.STATUS.present
                    }
                )
        return HttpResponseRedirect(course.get_absences_url())
