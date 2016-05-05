from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.core.urlresolvers import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, \
                                ListView, UpdateView, FormView
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe

from registrations.models import Child
from schools.models import Teacher
from schools.forms import TeacherForm, TeacherImportForm
from schools.utils import load_teachers


from .mixins import BackendMixin

__all__ = ['TeacherDetailView', 'TeacherListView',
           'TeacherCreateView',  'TeacherUpdateView',
           'TeacherDeleteView', 'TeacherImportView']


class TeacherDetailView(BackendMixin, DetailView):
    model = Teacher
    template_name = 'backend/teacher/detail.html'

    def get_context_data(self, **kwargs):
        context = {'students': Child.objects.filter(teacher=self.get_object())\
                                            .select_related('family',)\
                                            .prefetch_related('registrations', 'registrations__course__activity')
                   }
        return super(TeacherDetailView, self).get_context_data(**context)
    

class TeacherListView(BackendMixin, ListView):
    model = Teacher
    template_name = 'backend/teacher/list.html'
    queryset = Teacher.objects.prefetch_related('years')
    


class TeacherCreateView(BackendMixin, SuccessMessageMixin, CreateView):
    model = Teacher
    form_class = TeacherForm
    template_name = 'backend/teacher/create.html'
    success_url = reverse_lazy('backend:teacher-list')
    success_message = _('<a href="%(url)s" class="alert-link">Teacher %(name)s)</a> has been created.')
    
    def get_success_message(self, cleaned_data):
        url = self.object.get_backend_url()
        return mark_safe(self.success_message % {'url': url,
                                                 'name': self.object.get_full_name()})


class TeacherUpdateView(BackendMixin, SuccessMessageMixin, UpdateView):
    model = Teacher
    form_class = TeacherForm
    template_name = 'backend/teacher/update.html'
    success_url = reverse_lazy('backend:teacher-list')
    success_message = _("Teacher has been updated.")


class TeacherDeleteView(BackendMixin, SuccessMessageMixin, DeleteView):
    model = Teacher
    template_name = 'backend/teacher/confirm_delete.html'
    success_url = reverse_lazy('backend:teacher-list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        messages.add_message(self.request, messages.SUCCESS,
                             _("Teacher %(name)s has been deleted.") % {
                                'name': self.object.get_full_name()
                             })
        return super(TeacherDeleteView, self).delete(request, *args, **kwargs)


class TeacherImportView(BackendMixin, SuccessMessageMixin, FormView):
    form_class = TeacherImportForm
    success_url = reverse_lazy('backend:teacher-list')
    success_message = _("Teachers have been imported")
    template_name = 'backend/teacher/import.html'

    def form_valid(self, form):
        try:
            (created, updated, skipped) = load_teachers(self.request.FILES['thefile'])
        except ValueError, msg:
            context = self.get_context_data()
            context['form'] = form
            messages.add_message(self.request, messages.ERROR, msg)
            return self.render_to_response(context)
        self.success_message = _("%i teachers have been created, %i have been updated. %i were skipped because they are not responsible of a class.") % (created, updated, skipped)
        return super(TeacherImportView, self).form_valid(form)