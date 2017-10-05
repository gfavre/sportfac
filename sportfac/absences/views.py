from django.views.generic import DetailView

from activities.views import InstructorMixin
from activities.models import Course
from registrations.models import ChildActivityLevel
from .models import Absence


class AbsenceView(InstructorMixin, DetailView):
    model = Course
    template_name = 'absences/absences.html'
    pk_url_kwarg = 'course'
    queryset = Course.objects.prefetch_related('sessions', 'sessions__absences', 'participants__child')
    
    def get_context_data(self, **kwargs):
        context = super(AbsenceView, self).get_context_data(**kwargs)
        course = self.get_object()
        all_absences = dict(
            [((absence.child, absence.session), absence.status) for absence 
                                                                in Absence.objects.filter(session__course=course)]
        )
        context['absence_matrix'] = [[all_absences.get((registration.child, session), 'present') for session 
                                                                     in course.sessions.all()] 
         for registration in course.participants.all()]
        context['levels'] = ChildActivityLevel.LEVELS
        context['courses_list'] = self.request.user.course.all()
        return context