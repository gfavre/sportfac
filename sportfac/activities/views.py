# Create your views here.
from django.views.generic import DetailView, ListView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from .models import Activity
from sportfac.utils import WizardMixin



class LoginRequiredMixin(object):
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(request, *args, **kwargs)


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
