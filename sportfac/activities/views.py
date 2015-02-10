from django.views.generic import DetailView, ListView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse, reverse_lazy

from braces.views import GroupRequiredMixin, LoginRequiredMixin

from backend import RESPONSIBLE_GROUP
from sportfac.views import WizardMixin
from mailer.views import MailView, MailCreateView, CustomMailMixin, MailParticipantsView

from .models import Activity, Course

__all__ = ('ResponsibleMixin', 'ActivityDetailView', 'ActivityListView', 
           'MyCoursesListView', 'MyCourseDetailView')

class ResponsibleMixin(GroupRequiredMixin, LoginRequiredMixin):
    """Mixin for backend. Ensure that the user is logged in and is a member 
       of sports responisbles group."""
    group_required = RESPONSIBLE_GROUP


class CourseAccessMixin(ResponsibleMixin):
    def check_membership(self, group):
        if not super(CourseAccessMixin, self).check_membership(group):
            return self.request.user in [p.child.family for p in self.get_object().participants.all()]
        return True

class ActivityDetailView(DetailView):
    model = Activity
    
    def get_queryset(self):
        prefetched = Activity.objects.prefetch_related('courses', 'courses__participants', 'courses__responsible')
        return prefetched.all()
    
    def get_context_data(self, **kwargs):
        context = super(ActivityDetailView, self).get_context_data(**kwargs)
        activity = kwargs['object']
        if not self.request.user.is_authenticated():
            context['registrations'] = {}
            return context
        
        registrations = {}
        children = self.request.user.children.all()
        for course in activity.courses.all():
            participants = [reg.child for reg in course.participants.all()]
            for child in children:
                if child in participants:
                    registrations[course] = participants
                    break
            
        context['registrations'] = registrations
        return context


class ActivityListView(LoginRequiredMixin, WizardMixin, ListView):
    model = Activity


class MyCoursesListView(ResponsibleMixin, ListView):
    template_name = 'activities/course_list.html'

    def get_queryset(self):
        return Course.objects.filter(responsible=self.request.user)


class MyCourseDetailView(CourseAccessMixin, DetailView):
    model = Course
    template_name = 'activities/course_detail.html'
    slug_field = 'number'
    slug_url_kwarg = 'course'
    queryset = Course.objects.select_related('activity', 
                                             'responsible' 
                            ).prefetch_related( 'participants__child__school_year', 'participants__child__family')


class CustomMailCreateView(ResponsibleMixin, MailCreateView):
    template_name = 'activities/mail-create.html'
    
    def get_success_url(self):
        course = self.kwargs['course']                
        return reverse('activities:mail-preview', 
                       kwargs={'course': course })
          
class CustomMailPreview(ResponsibleMixin, CustomMailMixin, MailParticipantsView):
    template_name = 'activities/mail-preview-editlink.html'
        
    def get_success_url(self):
        return reverse('activities:course-detail', kwargs=self.kwargs)
    
    def get_from_address(self):
        return self.request.user.get_from_address()
     
    def post(self, request, *args, **kwargs):
        redirect = super(CustomMailPreview, self).post(request, *args, **kwargs)
        del self.request.session['mail']
        return redirect 
