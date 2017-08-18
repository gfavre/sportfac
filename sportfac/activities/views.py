# -*- coding: utf-8 -*-
import json

from django.core.urlresolvers import reverse
from django.db.models import Min, Max
from django.http import HttpResponseRedirect
from django.views.generic import DetailView, ListView
from django.views.generic.base import View
from django.views.generic.detail import SingleObjectMixin

from braces.views import GroupRequiredMixin, LoginRequiredMixin

from backend import INSTRUCTORS_GROUP
from mailer.views import (MailCreateView, ParticipantsMailCreateView, CustomMailMixin,
                          MailParticipantsView, MailCourseInstructorsView)
from mailer.forms import CourseMailForm
from sportfac.views import WizardMixin

from .models import Activity, Course


__all__ = ('InstructorMixin', 'ActivityDetailView', 'ActivityListView',
           'CustomParticipantsCustomMailView',
           'MyCoursesListView', 'MyCourseDetailView')


class InstructorMixin(GroupRequiredMixin, LoginRequiredMixin):
    """Mixin for backend. Ensure that the user is logged in and is a member 
       of sports responisbles group."""
    group_required = INSTRUCTORS_GROUP


class CourseAccessMixin(InstructorMixin):
    def check_membership(self, group):
        if not super(CourseAccessMixin, self).check_membership(group):
            return self.request.user in [p.child.family for p in self.get_object().participants.all()]
        return True


class ActivityDetailView(DetailView):
    model = Activity
    
    def get_queryset(self):
        prefetched = Activity.objects.prefetch_related('courses', 'courses__participants', 'courses__instructors')
        return prefetched.all()
    
    def get_context_data(self, **kwargs):
        context = super(ActivityDetailView, self).get_context_data(**kwargs)
        activity = kwargs['object']
        if not self.request.user.is_authenticated():
            context['registrations'] = {}
            return context
        
        registrations = {}
        children = self.request.user.children.all()
        for course in activity.courses.prefetch_related('participants__child'):
            participants = [reg.child for reg in course.participants.all()]
            for child in children:
                if child in participants:
                    registrations[course] = participants
                    break
            
        context['registrations'] = registrations
        return context


class ActivityListView(LoginRequiredMixin, WizardMixin, ListView):
    model = Activity
    
    def get_context_data(self, **kwargs):
        context = super(ActivityListView, self).get_context_data(**kwargs)
        from backend.dynamic_preferences_registry import global_preferences_registry
        context['MAX_REGISTRATIONS'] = global_preferences_registry.manager()['MAX_REGISTRATIONS']
        times = Course.objects.visible().aggregate(Max('end_time'), Min('start_time'))
        context['START_HOUR'] = times['start_time__min'].hour
        if times['end_time__max'].minute == 0:
            context['END_HOUR'] = times['end_time__max'].hour
        else:
            context['END_HOUR'] = (times['end_time__max'].hour + 1) % 24
        return context
    

class MyCoursesListView(InstructorMixin, ListView):
    template_name = 'activities/course_list.html'

    def get_queryset(self):
        return Course.objects.filter(instructors=self.request.user)


class MyCourseDetailView(CourseAccessMixin, DetailView):
    model = Course
    template_name = 'activities/course_detail.html'
    pk_url_kwarg = 'course'
    queryset = Course.objects.select_related('activity').\
        prefetch_related('participants__child__school_year', 'participants__child__family', 'instructors')


class CustomMailCreateView(InstructorMixin, ParticipantsMailCreateView):
    template_name = 'activities/mail-create.html'
    form_class = CourseMailForm

    def get_success_url(self):
        course = self.kwargs['course']                
        return reverse('activities:mail-preview', kwargs={'course': course})


class CustomMailPreview(InstructorMixin, CustomMailMixin, MailParticipantsView):
    template_name = 'activities/mail-preview-editlink.html'
        
    def get_success_url(self):
        return reverse('activities:course-detail', kwargs=self.kwargs)
    
    def get_from_address(self):
        return self.request.user.get_from_address()
     
    def post(self, request, *args, **kwargs):
        redirect = super(CustomMailPreview, self).post(request, *args, **kwargs)
        try:
            del self.request.session['mail']
            del self.request.session['mail-userids']
        except KeyError:
            pass

        return redirect 


class CustomParticipantsCustomMailView(InstructorMixin, SingleObjectMixin, View):
    model = Course
    pk_url_kwarg = 'course'

    def post(self, request, *args, **kwargs):
        course = self.get_object()
        userids = list(set(json.loads(request.POST.get('data', '[]'))))
        self.request.session['mail-userids'] = userids
        return HttpResponseRedirect(course.get_custom_mail_instructors_url())


class InstructorsMailView(InstructorMixin, MailCourseInstructorsView):
    template_name = 'activities/confirm_send.html'
    
    def get_success_url(self):
        return reverse('activities:my-courses')
