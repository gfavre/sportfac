from datetime import datetime, timedelta

from django.core.urlresolvers import reverse_lazy
from django.views.generic import FormView, TemplateView
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.db.models import Count, Max, Sum, Avg

from constance import config
from activities.models import Activity, Course
from profiles.models import FamilyUser, Registration, Child, Teacher, SchoolYear
from backend.forms import RegistrationDatesForm
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
        context['total_responsibles'] =  courses.values('responsible').distinct().count()
        context['last_course_update'] = courses.aggregate(
                                            latest=Max('modified'))['latest']
        
        return context
    
    def get_additional_context_phase2(self, context):
        def time_str_to_milliseconds(time_str):
            return 1000 * int(datetime.strptime(time_str, '%Y-%m-%d').strftime('%s'))
        
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
        registrations = Registration.objects.filter(
            created__range=(config.START_REGISTRATION,
                            config.END_REGISTRATION)
            ).extra({'creation': "to_char(profiles_registration.created, 'YYYY-MM-DD')"}
            ).values('creation'
            ).order_by('creation'
            ).annotate(num=Count('id'))
        context['registrations_per_day'] = [[time_str_to_milliseconds(reg.get('creation')),
                                             reg.get('num')] for reg in registrations]
        
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
        def time_str_to_milliseconds(time_str):
            return 1000 * int(datetime.strptime(time_str, '%Y-%m-%d').strftime('%s'))
        
        courses = Course.objects.all()
        context['nb_courses'] = courses.count()
        activities = Activity.objects.all()
        context['nb_activities'] = activities.count()
        context['total_sessions'] = courses.aggregate(Sum('number_of_sessions')).values()[0]
        context['total_responsibles'] =  courses.values('responsible').distinct().count()
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
        context['paid'] = finished.filter(total__gt=0, paid=True).count()
        registrations = Registration.objects.filter(
            created__range=(config.START_REGISTRATION,
                            config.END_REGISTRATION)
            ).extra({'creation': "to_char(profiles_registration.created, 'YYYY-MM-DD')"}
            ).values('creation'
            ).order_by('creation'
            ).annotate(num=Count('id'))
        context['registrations_per_day'] = [[time_str_to_milliseconds(reg.get('creation')),
                                             reg.get('num')] for reg in registrations]
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
    
    def form_valid(self, form):
        form.save_to_constance()
        messages.add_message(self.request, messages.SUCCESS, _("Opening and closing dates have been changed"))
        return super(RegistrationDatesView, self).form_valid(form)

    def form_invalid(self, form):
        messages.add_message(self.request, messages.ERROR,
                             mark_safe(_("An error was found in form %s") % form.non_field_errors()))
        return super(RegistrationDatesView, self).form_invalid(form)
