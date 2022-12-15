from __future__ import absolute_import

import datetime

from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from absences.models import Session
from activities.models import CoursesInstructors
from dateutil.relativedelta import relativedelta
from payroll.forms import FunctionForm, PayrollExportForm
from payroll.models import Function

from .mixins import BackendMixin


# TODO: think about a functiondetailview that lists all instructors of a given function and their associated course.


class FunctionListView(BackendMixin, ListView):
    model = Function
    template_name = "backend/payroll/function_list.html"


class FunctionCreateView(BackendMixin, SuccessMessageMixin, CreateView):
    model = Function
    form_class = FunctionForm
    template_name = "backend/payroll/function_create.html"
    success_url = reverse_lazy("backend:function-list")
    success_message = _("Function %(name)s has been created.")

    def get_success_message(self, cleaned_data):
        return mark_safe(self.success_message % {"name": self.object.name})


class FunctionDeleteView(BackendMixin, DeleteView):
    model = Function
    template_name = "backend/payroll/function_confirm_delete.html"
    success_url = reverse_lazy("backend:function-list")


class FunctionUpdateView(BackendMixin, SuccessMessageMixin, UpdateView):
    model = Function
    form_class = FunctionForm
    template_name = "backend/payroll/function_update.html"
    success_url = reverse_lazy("backend:function-list")
    success_message = _("Function has been updated.")


class SupervisorRolesList(BackendMixin, ListView):
    model = CoursesInstructors
    template_name = "backend/payroll/supervisor_roles_list.html"

    def get_queryset(self):
        return CoursesInstructors.objects.select_related(
            "course", "course__activity", "instructor", "function"
        ).all()

    def get_context_data(self, **kwargs):
        context = super(SupervisorRolesList, self).get_context_data(**kwargs)
        context["functions"] = Function.objects.all()
        return context


class PayrollReportView(BackendMixin, ListView):
    model = CoursesInstructors
    template_name = "backend/payroll/payroll_report.html"

    def get_start_end(self):
        start = now() - relativedelta(days=29)
        end = now()
        if "start" in self.request.GET:
            try:
                start = datetime.datetime.strptime(
                    self.request.GET.get("start"), "%Y-%m-%d"
                ).date()
            except ValueError:
                pass
        if "end" in self.request.GET:
            try:
                end = datetime.datetime.strptime(self.request.GET.get("end"), "%Y-%m-%d").date()
            except ValueError:
                pass
        return start, end

    def get_queryset(self):
        qs = super(PayrollReportView, self).get_queryset().select_related("course", "instructor")
        start, end = self.get_start_end()
        sessions = Session.objects.filter(date__gte=start, date__lte=end).values_list(
            "course", "instructor", "export_date"
        )
        exported_count = {}
        not_exported_count = {}
        for (course_id, instructor_id, export_date) in sessions:
            if export_date is not None:
                exported_count[(course_id, instructor_id)] = (
                    exported_count.get((course_id, instructor_id), 0) + 1
                )
            else:
                not_exported_count[(course_id, instructor_id)] = (
                    not_exported_count.get((course_id, instructor_id), 0) + 1
                )
        for course_instructor in qs:
            course_instructor.exported_count = exported_count.get(
                (course_instructor.course_id, course_instructor.instructor_id), 0
            )
            course_instructor.not_exported_count = not_exported_count.get(
                (course_instructor.course_id, course_instructor.instructor_id), 0
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super(PayrollReportView, self).get_context_data(**kwargs)
        context["start"], context["end"] = self.get_start_end()
        if "form" not in kwargs:
            context["form"] = PayrollExportForm()
        return context

    def post(self, request, *args, **kwargs):
        start, end = self.get_start_end()
        form = PayrollExportForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.start = start
            obj.end = end
            obj.exported_by = request.user
            obj.save()
            obj.generate_csv()
            filename = obj.csv_file.name.split("/")[-1]
            response = HttpResponse(obj.csv_file.file, content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="{0}"'.format(filename)
            return response
        else:
            return self.render_to_response(self.get_context_data(form=form))
