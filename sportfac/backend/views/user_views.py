import collections
import json
import tempfile

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Case, Count, When
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import urlencode
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, UpdateView, View

from absences.models import Absence
from profiles.forms import InstructorForm, ManagerForm, SetPasswordForm
from profiles.models import FamilyUser
from profiles.resources import InstructorResource, UserResource
from registrations.forms import ChildForm, ChildUpdateForm
from registrations.models import Bill, Child, ChildActivityLevel, Registration

from ..forms import ChildImportForm
from ..tasks import import_children
from .mixins import BackendMixin, ExcelResponseMixin, FullBackendMixin


class MailUsersView(BackendMixin, View):
    def post(self, request, *args, **kwargs):
        userids = list(set(json.loads(request.POST.get("data", "[]"))))
        self.request.session["mail-userids"] = userids
        params = ""
        if "prev" in request.GET:
            params += "?prev=" + urlencode(request.GET.get("prev"))
        return HttpResponseRedirect(reverse("backend:custom-mail-custom-users") + params)


class InstructorMixin:
    @staticmethod
    def get_queryset():
        return (
            FamilyUser.objects.filter(is_active=True).annotate(num_courses=Count("course")).filter(num_courses__gt=0)
        )


class ManagerMixin:
    @staticmethod
    def get_queryset():
        return FamilyUser.objects.filter(is_manager=True, is_active=True)


class UserListView(BackendMixin, ListView):
    model = FamilyUser
    template_name = "backend/user/list.html"

    def get_queryset(self):
        qs = FamilyUser.active_objects.all()
        user: FamilyUser = self.request.user
        if user.is_restricted_manager:
            registrations = Registration.objects.filter(course__activity__in=user.managed_activities.all())
            qs = qs.filter(children__registrations__in=registrations).distinct()

        qs = (
            qs.annotate(num_children=Count("children"))
            .annotate(
                valid_registrations=Count(
                    Case(When(children__registrations__in=Registration.objects.validated(), then=1))
                ),
                waiting_registrations=Count(
                    Case(When(children__registrations__in=Registration.objects.waiting(), then=1))
                ),
                opened_bills=Count(Case(When(bills__status=Bill.STATUS.waiting, then=1))),
            )
            .prefetch_related("children")
        )

        return qs

    def post(self, request, *args, **kwargs):
        data = json.loads(request.POST.get("data", "[]"))
        if data == -1:
            self.request.session["mail-userids"] = [str(id) for id in FamilyUser.objects.values_list("id", flat=True)]
        else:
            self.request.session["mail-userids"] = list(set(data))
        return HttpResponseRedirect(reverse("backend:custom-mail-custom-users"))


class InstructorListView(InstructorMixin, UserListView):
    template_name = "backend/user/instructor-list.html"


class UserExportView(FullBackendMixin, ExcelResponseMixin, View):
    filename = _("users")
    resource_class = UserResource


class ManagerExportView(FullBackendMixin, ExcelResponseMixin, ManagerMixin, View):
    filename = _("managers")
    resource_class = InstructorResource


class ManagerListView(FullBackendMixin, ManagerMixin, UserListView):
    template_name = "backend/user/manager-list.html"


class InstructorExportView(FullBackendMixin, ExcelResponseMixin, InstructorMixin, View):
    filename = _("instructors")
    resource_class = InstructorResource


class UserCreateView(FullBackendMixin, SuccessMessageMixin, CreateView):
    model = FamilyUser
    form_class = ManagerForm
    template_name = "backend/user/create.html"
    success_url = reverse_lazy("backend:user-list")

    def form_valid(self, form):
        self.object = form.save()
        self.object.set_password(form.cleaned_data["password1"])
        self.object.save()
        self.object.is_manager = form.cleaned_data["is_manager"]
        return super().form_valid(form)

    def get_success_message(self, cleaned_data):
        return _("User %s has been added.") % self.object.full_name


class ManagerCreateView(UserCreateView):
    success_url = reverse_lazy("backend:manager-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_manager"] = True
        return ctx

    def get_initial(self):
        initial = super().get_initial()
        initial["is_manager"] = True
        return initial

    def get_success_message(self, cleaned_data):
        return _("Manager %s has been added.") % self.object.full_name


class RestrictedAdminListView(FullBackendMixin, ListView):
    model = FamilyUser
    template_name = "backend/user/restricted-admin-list.html"

    def get_queryset(self):
        return FamilyUser.objects.filter(is_restricted_manager=True, is_active=True)


class InstructorCreateView(UserCreateView):
    success_url = reverse_lazy("backend:instructor-list")
    form_class = InstructorForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_instructor"] = True
        return ctx

    def form_valid(self, form):
        self.object = form.save()
        self.object.is_manager = form.cleaned_data["is_manager"]
        return super().form_valid(form)

    def get_success_message(self, cleaned_data):
        return _("Instructor %s has been added.") % self.object.full_name


class UserUpdateView(BackendMixin, SuccessMessageMixin, UpdateView):
    model = FamilyUser
    template_name = "backend/user/update.html"

    def get_initial(self):
        initial = super().get_initial()
        initial["is_manager"] = self.object.is_manager
        return initial

    def get_form_class(self):
        if self.object.is_instructor:
            return InstructorForm
        return ManagerForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # noinspection PyUnresolvedReferences
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_instructor"] = self.object.is_instructor
        return ctx

    def form_valid(self, form):
        self.object = form.save()
        self.object.is_manager = form.cleaned_data["is_manager"]
        self.object.save()
        return super().form_valid(form)

    def get_success_url(self):
        if self.object.is_instructor:
            return reverse_lazy("backend:instructor-list")
        return reverse_lazy("backend:user-list")

    def get_success_message(self, cleaned_data):
        return _("Contact informations of %s have been updated.") % self.object.full_name


class UserDeleteView(FullBackendMixin, SuccessMessageMixin, DeleteView):
    model = FamilyUser
    success_url = reverse_lazy("backend:user-list")
    success_message = _("User %(user)s has been deleted.")
    template_name = "backend/user/confirm_delete.html"

    def delete(self, request, *args, **kwargs):
        # noinspection PyAttributeOutsideInit
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.soft_delete()
        messages.success(self.request, self.get_success_message({"user": self.object.full_name}))
        return HttpResponseRedirect(success_url)


class UserDetailView(BackendMixin, DetailView):
    model = FamilyUser

    def get_template_names(self):
        user = self.get_object()
        template_names = ["backend/user/detail.html"]
        if user.is_instructor:
            template_names = ["backend/user/detail-instructor.html"] + template_names
        return template_names  # noqa: R504


class InstructorDetailView(BackendMixin, DetailView):
    model = FamilyUser
    template_name = "backend/user/detail-instructor.html"


class PasswordSetView(BackendMixin, SuccessMessageMixin, FormView):
    form_class = SetPasswordForm
    template_name = "backend/user/password-change.html"

    def get_success_message(self, cleaned_data):
        return _("Password changed for user %s.") % self.get_object()

    def get_success_url(self):
        return self.get_object().get_backend_url()

    def get_object(self):
        user_id = self.kwargs.get("user", None)
        return get_object_or_404(FamilyUser, pk=user_id)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.get_object()
        return kwargs

    def form_valid(self, form):
        user = self.get_object()
        user.set_password(form.cleaned_data["new_password1"])
        user.save()
        return super().form_valid(form)


class ChildMixin(BackendMixin):
    def get_queryset(self):
        # noinspection PyUnresolvedReferences
        user: FamilyUser = self.request.user
        qs = Child.objects.select_related("family", "school_year", "school", "building")
        if user.is_restricted_manager:
            registrations = Registration.objects.filter(course__activity__in=user.managed_activities.all())
            return qs.filter(registrations__in=registrations).distinct()
        return qs


class ChildDetailView(ChildMixin, DetailView):
    model = Child
    template_name = "backend/user/child-detail.html"
    pk_url_kwarg = "child"
    slug_url_kwarg = "lagapeo"
    slug_field = "id_lagapeo"


class ChildListView(ChildMixin, ListView):
    model = Child
    template_name = "backend/user/child-list.html"


class ChildCreateView(FullBackendMixin, SuccessMessageMixin, CreateView):
    model = Child
    form_class = ChildForm
    template_name = "backend/user/child-create.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "user" in self.kwargs:
            context["family"] = get_object_or_404(FamilyUser, pk=self.kwargs["user"])
        return context

    def get_initial(self):
        initial = super().get_initial()
        if "user" in self.kwargs:
            initial = initial.copy()
            initial["family"] = get_object_or_404(FamilyUser, pk=self.kwargs["user"])
        return initial

    def get_success_url(self):
        if "user" in self.kwargs:
            return get_object_or_404(FamilyUser, pk=self.kwargs["user"]).get_backend_url()
        return reverse("backend:child-list")

    def get_success_message(self, cleaned_data):
        return

    def form_valid(self, form):
        child = form.save(commit=False)
        if "user" in self.kwargs:
            user = get_object_or_404(FamilyUser, pk=self.kwargs["user"])
            child.family = user
        child.save()
        messages.success(self.request, _("Child %s has been added.") % child.full_name)
        return HttpResponseRedirect(self.get_success_url())


class ChildUpdateView(ChildMixin, SuccessMessageMixin, UpdateView):
    model = Child
    form_class = ChildUpdateForm
    template_name = "backend/user/child-update.html"
    success_url = reverse_lazy("backend:child-list")
    pk_url_kwarg = "child"

    def get_success_message(self, cleaned_data):
        return _("Child %s has been updated.") % self.object.full_name


class ChildAbsencesView(ChildMixin, DetailView):
    model = Child
    pk_url_kwarg = "child"
    template_name = "backend/user/absences.html"

    def get_context_data(self, **kwargs):
        child = self.get_object()
        qs = (
            Absence.objects.filter(child=child)
            .select_related("session", "session__course", "session__course__activity")
            .order_by("session__course__activity", "session__course")
        )
        kwargs["all_dates"] = list(set(qs.values_list("session__date", flat=True)))
        kwargs["all_dates"].sort()
        course_absences = collections.OrderedDict()
        activity_absences = collections.OrderedDict()
        for absence in qs:
            if absence.session.course in course_absences:
                course_absences[absence.session.course][absence.session.date] = absence
            else:
                course_absences[absence.session.course] = {absence.session.date: absence}

        for course, absences in course_absences.items():
            if course.activity in activity_absences:
                activity_absences[course.activity].append((course, absences))
            else:
                activity_absences[course.activity] = [(course, absences)]
        kwargs["activity_absences"] = activity_absences
        kwargs["course_absences"] = course_absences
        kwargs["levels"] = ChildActivityLevel.LEVELS

        return super().get_context_data(**kwargs)


class ChildDeleteView(FullBackendMixin, SuccessMessageMixin, DeleteView):
    model = Child
    template_name = "backend/user/child-confirm_delete.html"
    success_url = reverse_lazy("backend:child-list")
    success_message = _("Child has been removed.")
    pk_url_kwarg = "child"


class ChildImportView(FullBackendMixin, SuccessMessageMixin, FormView):
    form_class = ChildImportForm
    success_url = reverse_lazy("backend:child-list")
    success_message = _("Children are being imported")
    template_name = "backend/user/child-import.html"

    def form_valid(self, form):
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        for chunk in self.request.FILES["thefile"].chunks():
            temp_file.write(chunk)
        temp_file.close()
        import_children.delay(temp_file.name, tenant_id=self.request.tenant.pk, user_id=str(self.request.user.pk))
        return super().form_valid(form)
