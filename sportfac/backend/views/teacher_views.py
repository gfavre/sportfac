from django.core.urlresolvers import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, \
                                ListView, UpdateView

from profiles.models import Teacher, Child
from profiles.forms import TeacherForm

from .mixins import BackendMixin

__all__ = ['TeacherDetailView', 'TeacherListView',
           'TeacherCreateView',  'TeacherUpdateView',
           'TeacherDeleteView']


class TeacherDetailView(BackendMixin, DetailView):
    model = Teacher
    template_name = 'backend/teacher/detail.html'

    def get_context_data(self, **kwargs):
        context = {'students': Child.objects.filter(teacher=self.get_object())\
                                            .select_related('family')
                   }
        return super(TeacherDetailView, self).get_context_data(**context)
    

class TeacherListView(BackendMixin, ListView):
    model = Teacher
    template_name = 'backend/teacher/list.html'
    queryset = Teacher.objects.prefetch_related('years')
    


class TeacherCreateView(BackendMixin, CreateView):
    model = Teacher
    form_class = TeacherForm
    template_name = 'backend/teacher/create.html'


class TeacherUpdateView(BackendMixin, UpdateView):
    model = Teacher
    form_class = TeacherForm
    template_name = 'backend/teacher/update.html'


class TeacherDeleteView(BackendMixin, DeleteView):
    model = Teacher
    template_name = 'backend/teacher/confirm_delete.html'
    success_url = reverse_lazy('backend:teacher-list')
