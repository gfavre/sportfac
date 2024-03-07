from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, UpdateView

from registrations.models import Child
from schools.forms import BuildingForm, TeacherForm, TeacherImportForm
from schools.models import Building, Teacher

from .mixins import FullBackendMixin


class TeacherDetailView(FullBackendMixin, DetailView):
    model = Teacher
    template_name = "backend/teacher/detail.html"

    def get_context_data(self, **kwargs):
        context = {
            "students": Child.objects.filter(teacher=self.get_object())
            .select_related(
                "family",
            )
            .prefetch_related("registrations", "registrations__course__activity")
        }
        return super().get_context_data(**context)


class TeacherListView(FullBackendMixin, ListView):
    model = Teacher
    template_name = "backend/teacher/list.html"
    queryset = Teacher.objects.prefetch_related("years", "buildings")


class TeacherCreateView(FullBackendMixin, SuccessMessageMixin, CreateView):
    model = Teacher
    form_class = TeacherForm
    template_name = "backend/teacher/create.html"
    success_url = reverse_lazy("backend:teacher-list")
    success_message = _('<a href="%(url)s" class="alert-link">Teacher %(name)s)</a> has been created.')

    def get_success_message(self, cleaned_data):
        url = self.object.get_backend_url()
        return mark_safe(self.success_message % {"url": url, "name": self.object.get_full_name()})


class TeacherUpdateView(FullBackendMixin, SuccessMessageMixin, UpdateView):
    model = Teacher
    form_class = TeacherForm
    template_name = "backend/teacher/update.html"
    success_url = reverse_lazy("backend:teacher-list")
    success_message = _("Teacher has been updated.")


class TeacherDeleteView(FullBackendMixin, SuccessMessageMixin, DeleteView):
    model = Teacher
    template_name = "backend/teacher/confirm_delete.html"
    success_url = reverse_lazy("backend:teacher-list")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        messages.add_message(
            self.request,
            messages.SUCCESS,
            _("Teacher %(name)s has been deleted.") % {"name": self.object.get_full_name()},
        )
        return super().delete(request, *args, **kwargs)


class TeacherImportView(FullBackendMixin, SuccessMessageMixin, FormView):
    form_class = TeacherImportForm
    success_url = reverse_lazy("backend:teacher-list")
    success_message = _("Teachers have been imported")
    template_name = "backend/teacher/import.html"

    def form_valid(self, form):
        from schools.utils import load_teachers

        try:
            (created, updated, skipped) = load_teachers(self.request.FILES["thefile"])
        except ValueError as msg:
            context = self.get_context_data()
            context["form"] = form
            messages.add_message(self.request, messages.ERROR, msg)
            return self.render_to_response(context)
        self.success_message = _(
            "%i teachers have been created, %i have been updated. "
            "%i were skipped because they are not responsible of a class."
        ) % (created, updated, skipped)
        return super().form_valid(form)


class BuildingDetailView(FullBackendMixin, DetailView):
    model = Building
    template_name = "backend/building/detail.html"


class BuildingListView(FullBackendMixin, ListView):
    model = Building
    template_name = "backend/building/list.html"
    queryset = Building.objects.prefetch_related("teachers")


class BuildingCreateView(FullBackendMixin, SuccessMessageMixin, CreateView):
    model = Building
    form_class = BuildingForm
    template_name = "backend/building/create.html"
    success_url = reverse_lazy("backend:building-list")
    success_message = _('<a href="%(url)s" class="alert-link">Building %(name)s)</a> has been created.')

    def get_success_message(self, cleaned_data):
        url = self.object.get_backend_url()
        return mark_safe(self.success_message % {"url": url, "name": self.object.name})


class BuildingUpdateView(FullBackendMixin, SuccessMessageMixin, UpdateView):
    model = Building
    form_class = BuildingForm
    template_name = "backend/building/update.html"
    success_url = reverse_lazy("backend:building-list")
    success_message = _("Building has been updated.")


class BuildingDeleteView(FullBackendMixin, SuccessMessageMixin, DeleteView):
    model = Building
    template_name = "backend/building/confirm_delete.html"
    success_url = reverse_lazy("backend:building-list")

    def delete(self, request, *args, **kwargs):
        building = self.get_object()
        messages.add_message(
            self.request,
            messages.SUCCESS,
            _("Building %(name)s has been deleted.") % {"name": building.name},
        )
        return super().delete(request, *args, **kwargs)


class BuildingTeacherImportView(FullBackendMixin, SuccessMessageMixin, FormView):
    form_class = TeacherImportForm
    success_url = reverse_lazy("backend:teacher-list")
    success_message = _("Teachers have been imported")
    template_name = "backend/teacher/import.html"

    def form_valid(self, form):
        from schools.utils import load_teachers

        try:
            (created, updated, skipped) = load_teachers(
                self.request.FILES["thefile"], building=form.cleaned_data["building"]
            )
        except ValueError as msg:
            context = self.get_context_data()
            context["form"] = form
            messages.add_message(self.request, messages.ERROR, msg)
            return self.render_to_response(context)
        self.success_message = _("%i teachers have been created, %i have been updated.") % (
            created,
            updated,
        )
        if skipped:
            self.success_message += (
                "<br>" + _("%i were skipped because they are not responsible of a class.") % skipped
            )

        return super().form_valid(form)
