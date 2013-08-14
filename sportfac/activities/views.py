# Create your views here.
from django.views.generic import DetailView, ListView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from .models import Activity
from profiles.models import Registration

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
        context['registrations'] = []

        if self.request.user.is_authenticated():
            reg = Registration.objects.filter(course__activity=kwargs['object'],
                                              child__in=self.request.user.children.all())
            registrations = Registration.objects.filter(course__activity=kwargs['object'],
                                                        child__in=self.request.user.children.all()).order_by('course')
            context['registrations'] = registrations
        return context


class ActivityListView(LoginRequiredMixin, ListView):
    model = Activity

