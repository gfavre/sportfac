from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from payroll.forms import FunctionForm
from payroll.models import Function
from .mixins import BackendMixin


# TODO: think about a functiondetailview that lists all instructors of a given function and their associated course.


class FunctionListView(BackendMixin, ListView):
    model = Function
    template_name = 'backend/payroll/function_list.html'


class FunctionCreateView(BackendMixin, SuccessMessageMixin, CreateView):
    model = Function
    form_class = FunctionForm
    template_name = 'backend/payroll/function_create.html'
    success_url = reverse_lazy('backend:function-list')
    success_message = _('Function %(name)s has been created.')

    def get_success_message(self, cleaned_data):
        return mark_safe(self.success_message % {'name': self.object.name})


class FunctionDeleteView(BackendMixin, DeleteView):
    model = Function
    template_name = 'backend/payroll/function_confirm_delete.html'
    success_url = reverse_lazy('backend:function-list')


class FunctionUpdateView(BackendMixin, SuccessMessageMixin, UpdateView):
    model = Function
    form_class = FunctionForm
    template_name = 'backend/payroll/function_update.html'
    success_url = reverse_lazy('backend:function-list')
    success_message = _("Function has been updated.")
