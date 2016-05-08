from datetime import datetime, timedelta
import time

from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse_lazy
from django.views.generic import FormView, TemplateView
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.db.models import Count, Max, Sum, Avg

from activities.models import Activity, Course
from profiles.models import FamilyUser, SchoolYear
from registrations.models import Child, Registration
from schools.models import Teacher
from backend.forms import RegistrationDatesForm
from backend import MANAGERS_GROUP, RESPONSIBLE_GROUP
from .mixins import BackendMixin

__all__ = ('HomePageView', 'RegistrationDatesView',)


###############################################################################
# Homepage
       

class HomePageView(BackendMixin, TemplateView):
    
    def get_template_names(self):
        return 'backend/dashboard-phase%i.html' % self.request.PHASE
    
    def get_additional_context_phase1(self, context):
        context['nb_teachers'] = Teacher.objects.count()
        context['last_teacher_update'] = Teacher.objects.aggregate(
                                            latest=Max('modified'))['latest']
        years = SchoolYear.objects\
                          .annotate(num_teachers=(Count('teacher')))\
                          .filter(num_teachers__gt=0)
        context['teachers_per_year'] = [(year.get_year_display(), year.num_teachers) for year in years]
        
        courses = Course.objects.all()
        context['nb_courses'] = courses.count()
        activities = Activity.objects.all()
        context['nb_activities'] = activities.count()

        context['ready_courses'] = courses.filter(uptodate=True).count()
        context['notready_courses'] = context['nb_courses'] - context['ready_courses']
        context['total_sessions'] = courses.aggregate(Sum('number_of_sessions')).values()[0]
        context['total_responsibles'] = Group.objects.get(name=RESPONSIBLE_GROUP).user_set.count()
        
        context['last_course_update'] = courses.aggregate(
                                            latest=Max('modified'))['latest']
        
        return context
    
    def _get_registrations_per_day(self):
        total_per_day = {}
        start = self.request.tenant.preferences['phase__START_REGISTRATION']
        end = self.request.tenant.preferences['phase__END_REGISTRATION']
        registrations = [d.date() for d in Registration.objects\
                                                       .filter(created__range=(start, end))\
                                                       .values_list('created', flat=True)]
        for date in registrations:
            milliseconds = int(time.mktime(date.timetuple()) * 1000)
            total = total_per_day.setdefault(milliseconds, 0)
            total_per_day[milliseconds] += 1
        
        return [[k, total_per_day[k]] for k in sorted(total_per_day)]
    
    def get_additional_context_phase2(self, context):
        finished = FamilyUser.objects.filter(finished_registration=True)
        waiting = set(Registration.objects\
                                      .filter(status=Registration.STATUS.waiting)\
                                      .select_related('child__family')\
                                      .values_list('child__family'))
        valid = set(Registration.objects\
                                      .filter(status=Registration.STATUS.valid)\
                                      .select_related('child__family')\
                                      .values_list('child__family'))
        context['waiting'] = len(waiting)
        context['valid'] = len(valid)
        
        context['payement_due'] = finished.filter(total__gt=0).count()
        context['paid'] = finished.filter(total__gt=0, paid=True).count()
                    
        context['registrations_per_day'] = self._get_registrations_per_day()
        
        participants = Course.objects.annotate(count_participants=Count('participants'))\
                                     .values_list('min_participants', 
                                                  'max_participants', 
                                                  'count_participants')
        context['nb_courses'] = len(participants)
        context['nb_full_courses'] = 0
        context['nb_minimal_courses'] = 0
        
        for (min_participants, max_participants, count_participants) in participants:
            if min_participants <= count_participants:
                context['nb_minimal_courses'] += 1
                if max_participants == count_participants:
                    context['nb_full_courses'] += 1

        return context
    
    def get_additional_context_phase3(self, context):        
        courses = Course.objects.all()
        context['nb_courses'] = courses.count()
        activities = Activity.objects.all()
        context['nb_activities'] = activities.count()
        context['total_sessions'] = courses.aggregate(Sum('number_of_sessions')).values()[0]
        context['total_responsibles'] = Group.objects.get(name=RESPONSIBLE_GROUP).user_set.count()
        timedeltas = []
        for course in courses:
            timedeltas.append(course.number_of_sessions * course.duration)
        
        td = sum(timedeltas, timedelta())
        context['total_hours'] =  td.days * 24 + td.seconds / 3600
        context['total_remaining_minutes'] =  (td.seconds % 3600) / 60
        
        
        participants = Course.objects.annotate(count_participants=Count('participants'))\
                                     .values_list('min_participants', 
                                                  'max_participants', 
                                                  'count_participants')
        context['nb_courses'] = len(participants)
        context['nb_full_courses'] = 0
        context['nb_minimal_courses'] = 0
        
        for (min_participants, max_participants, count_participants) in participants:
            if min_participants <= count_participants:
                context['nb_minimal_courses'] += 1
                if max_participants == count_participants:
                    context['nb_full_courses'] += 1
        
        
        finished = FamilyUser.objects.filter(finished_registration=True)
        context['payement_due'] = finished.filter(total__gt=0).count()
        context['total_due'] = FamilyUser.objects.aggregate(Sum('total')).values()[0]
        paid = finished.filter(total__gt=0, paid=True)
        context['paid'] = paid.count()
        context['total_paid'] = paid.aggregate(Sum('total')).values()[0]

        context['registrations_per_day'] = self._get_registrations_per_day()
        
        context['nb_registrations'] = Registration.objects.count()
        context['nb_families'] = finished.count()
        context['nb_children'] = Child.objects.filter(family__finished_registration=True).count()
        return context
    
    def get_context_data(self, **kwargs):
        context = super(HomePageView, self).get_context_data(**kwargs)
        method_name = 'get_additional_context_phase%i' % self.request.PHASE
        context = getattr(self, method_name)(context)                              
        return context


###############################################################################
# Dates
class RegistrationDatesView(BackendMixin, FormView):
    template_name = 'backend/registration_dates.html'
    form_class = RegistrationDatesForm
    success_url = reverse_lazy('backend:home')
    
    def get_initial(self):
        initial = super(RegistrationDatesView, self).get_initial()
        initial['opening_date'] = self.request.tenant.preferences['phase__START_REGISTRATION']
        initial['closing_date'] = self.request.tenant.preferences['phase__END_REGISTRATION']      
        return initial
    
    def form_valid(self, form):
        self.request.tenant.preferences['phase__START_REGISTRATION'] = form.cleaned_data['opening_date']
        self.request.tenant.preferences['phase__END_REGISTRATION'] = form.cleaned_data['closing_date']
        messages.add_message(self.request, messages.SUCCESS, _("Opening and closing dates have been changed"))
        return super(RegistrationDatesView, self).form_valid(form)

    def form_invalid(self, form):
        messages.add_message(self.request, messages.ERROR,
                             mark_safe(_("An error was found in form %s") % form.non_field_errors()))
        return super(RegistrationDatesView, self).form_invalid(form)
