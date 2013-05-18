# Create your views here.
from django.views.generic import DetailView, ListView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from .models import Activity


class LoginRequiredMixin(object):
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(request, *args, **kwargs)



class ActivityDetailView(LoginRequiredMixin, DetailView):
    model = Activity


class ActivityListView(LoginRequiredMixin, ListView):
    model = Activity

