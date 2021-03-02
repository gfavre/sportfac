from collections import OrderedDict
from datetime import datetime, timedelta
import json
import time

from django.contrib import messages
from django.core.urlresolvers import reverse_lazy
from django.db import models
from django.db.models import Count, Max, Sum, Func
from django.views.generic import FormView, TemplateView
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import ugettext as _

from activities.models import Activity, Course, CoursesInstructors
from profiles.models import City, FamilyUser, SchoolYear
from registrations.models import Bill, Child, Registration
from schools.models import Teacher
from backend.forms import RegistrationDatesForm
from .mixins import BackendMixin


__all__ = ('HomePageView', 'RegistrationDatesView',)


###############################################################################
# Homepage
       

class Year(Func):
    function = 'EXTRACT'
    template = '%(function)s(YEAR from %(expressions)s)'
    output_field = models.IntegerField()


class Month(Func):
    function = 'EXTRACT'
    template = '%(function)s(MONTH from %(expressions)s)'
    output_field = models.IntegerField()


class HomePageView(BackendMixin, TemplateView):
    
    def get_template_names(self):
        return 'backend/dashboard-phase%i.html' % self.request.PHASE
    
    def get_additional_context_phase1(self, context):
        context['nb_teachers'] = Teacher.objects.count()
        context['last_teacher_update'] = Teacher.objects.aggregate(
                                            latest=Max('modified'))['latest'] or 'n/a'
        years = SchoolYear.visible_objects\
                          .annotate(num_teachers=(Count('teacher')))\
                          .filter(num_teachers__gt=0)
        context['teachers_per_year'] = [(year.get_year_display(), year.num_teachers) for year in years]
        
        courses = Course.objects.all()
        context['nb_courses'] = courses.count()
        activities = Activity.objects.all()
        context['nb_activities'] = activities.count()

        context['ready_courses'] = courses.filter(uptodate=True).count()
        context['notready_courses'] = context['nb_courses'] - context['ready_courses']
        context['total_sessions'] = courses.aggregate(Sum('number_of_sessions')).values()[0] or 0
        context['total_instructors'] = FamilyUser.instructors_objects.count()
        
        context['last_course_update'] = courses.aggregate(latest=Max('modified'))['latest'] or 'n/a'
        
        return context

    def _get_registrations_per_day(self):
        total_per_day = {}
        start = self.request.tenant.preferences['phase__START_REGISTRATION']
        end = self.request.tenant.preferences['phase__END_REGISTRATION']
        registrations = [d.date() for d in Registration.objects.filter(created__range=(start, end))
                                                               .values_list('created', flat=True)]

        for date in registrations:
            milliseconds = int(time.mktime(date.timetuple()) * 1000)
            total_per_day.setdefault(milliseconds, 0)
            total_per_day[milliseconds] += 1

        return [[k, total_per_day[k]] for k in sorted(total_per_day)]

    def _get_registrations_per_month(self):
        start = self.request.tenant.preferences['phase__START_REGISTRATION']
        end = self.request.tenant.preferences['phase__END_REGISTRATION']

        registrations = Registration.objects.filter(created__range=(start, end))\
            .order_by('created')\
            .annotate(year=Year('created'), month=Month('created')) \
            .order_by('year', 'month') \
            .values('year', 'month') \
            .annotate(total=Count('*')) \
            .values('year', 'month', 'total')
        from django.template.defaultfilters import date as _date

        return OrderedDict(
            (_date(datetime(reg['year'], reg['month'], 1), "b Y"), reg['total']) for reg in registrations
        )

    def get_additional_context_phase2(self, context):
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

        # noinspection PyUnresolvedReferences
        context['payement_due'] = Bill.waiting.filter(total__gt=0).count()
        # noinspection PyUnresolvedReferences
        context['paid'] = Bill.paid.filter(total__gt=0).count()
        
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

        context = self._add_cities_context(context)
        context = self._add_registrations_context(context)

        return context
    
    def get_additional_context_phase3(self, context):
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
        
        context['payement_due'] = Bill.waiting.count()
        paid = Bill.paid.all()
        context['paid'] = paid.count()
        context['total_due'] = Bill.objects.aggregate(Sum('total')).values()[0] or 0
        context['total_paid'] = paid.aggregate(Sum('total')).values()[0] or 0
        context = self._add_cities_context(context)
        context = self._add_registrations_context(context)
        return context

    def _add_cities_context(self, context):
        qs = Registration.objects.exclude(status__in=(Registration.STATUS.canceled,
                                                      Registration.STATUS.waiting)) \
            .select_related('child', 'child__family')
        context['nb_registrations'] = qs.count()
        children = set([reg.child for reg in qs])
        families = set([child.family for child in children])
        context['nb_families'] = len(families)
        context['nb_children'] = len(children)

        UNKNOWN = _("Unknown")
        children_per_zip = {UNKNOWN: set()}
        families_per_zip = {UNKNOWN: set()}

        cities = dict(
            City.objects.filter(zipcode__in=qs.values_list('child__family__zipcode').distinct()).values_list('zipcode',
                                                                                                             'name'))
        for zipcode, city in cities.items():
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

        children_per_zip_ordered = list([(zipcode, len(children)) for (zipcode, children) in children_per_zip.items()])
        children_per_zip_ordered.sort(lambda x, y: -cmp(x[1], y[1]))
        context['children_per_zip_labels'] = json.dumps(
            [u'{} {}'.format(zipcode, cities.get(zipcode, '')).strip()
             for zipcode, nb in children_per_zip_ordered])
        context['children_per_zip_data'] = json.dumps([nb for zipcode, nb in children_per_zip_ordered])

        families_per_zip_ordered = list([(zipcode, len(families)) for (zipcode, families) in families_per_zip.items()])
        families_per_zip_ordered.sort(lambda x, y: -cmp(x[1], y[1]))
        context['families_per_zip_labels'] = json.dumps(
            [u'{} {}'.format(zipcode, cities.get(zipcode, '')).strip()
             for zipcode, nb in families_per_zip_ordered])
        context['families_per_zip_data'] = json.dumps([nb for zipcode, nb in families_per_zip_ordered])

        return context

    def _add_registrations_context(self, context):
        start = self.request.tenant.preferences['phase__START_REGISTRATION']
        end = self.request.tenant.preferences['phase__END_REGISTRATION']
        if (end-start).days > 45:
            context['registrations_period'] = 'monthly'
            registrations = self._get_registrations_per_month()
            context['monthly_registrations_labels'] = json.dumps(registrations.keys())
            context['monthly_registrations_data'] = json.dumps(registrations.values())
        else:
            context['registrations_period'] = 'daily'
            context['registrations_per_day'] = self._get_registrations_per_day()
        return context

    def get_context_data(self, **kwargs):
        context = super(HomePageView, self).get_context_data(**kwargs)
        context['now'] = now()

        courses = Course.objects.all()
        context['nb_courses'] = courses.count()
        activities = Activity.objects.all()
        context['nb_activities'] = activities.count()
        context['total_sessions'] = courses.aggregate(Sum('number_of_sessions')).values()[0] or 0
        context['total_instructors'] = CoursesInstructors.objects.distinct('instructor').count()
        timedeltas = []
        for course in courses:
            timedeltas.append(course.number_of_sessions * course.duration)
        td = sum(timedeltas, timedelta())
        context['total_hours'] = td.days * 24 + td.seconds / 3600
        context['total_remaining_minutes'] = (td.seconds % 3600) / 60

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
