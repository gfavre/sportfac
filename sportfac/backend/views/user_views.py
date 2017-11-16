# -*- coding: utf-8 -*-
import collections
import json
import tempfile

from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import Group
from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse_lazy, reverse
from django.db.models import Count, Case, When
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import urlencode
from django.utils.translation import ugettext as _
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, View, FormView

from absences.models import Absence
from profiles.forms import ManagerForm, ManagerWithPasswordForm, InstructorForm, InstructorWithPasswordForm
from profiles.models import FamilyUser
from profiles.resources import UserResource, InstructorResource
from registrations.models import Bill, Child, ChildActivityLevel, Registration
from registrations.forms import ChildForm
from .mixins import BackendMixin, ExcelResponseMixin
from .. import MANAGERS_GROUP, INSTRUCTORS_GROUP
from ..forms import ChildImportForm
from ..tasks import import_children


__all__ = ('UserListView', 'UserCreateView', 'PasswordSetView',
           'UserUpdateView', 'UserDeleteView', 'UserDetailView',
           'UserExportView', 'MailUsersView',
           'ChildDetailView', 'ChildListView', 'ChildCreateView', 'ChildUpdateView',
           'ChildDeleteView', 'ChildImportView',
           'ChildAbsencesView',
           'ManagerListView', 'ManagerCreateView',  'ManagerExportView',
           'InstructorListView', 'InstructorCreateView', 'InstructorDetailView',
           'InstructorExportView',
           )

valid_registrations = Registration.objects.validated()

FamilyUser.objects.annotate(
    valid_registrations=Count(Case(When(children__registrations__in=Registration.objects.validated(), then=1))),
    waiting_registrations=Count(Case(When(children__registrations__in=Registration.objects.waiting(), then=1))),
    opened_bills=Count(Case(When(bills__status=Bill.STATUS.waiting, then=1))),
)


class UserListView(BackendMixin, ListView):
    model = FamilyUser
    template_name = 'backend/user/list.html'

    def get_queryset(self):
        return FamilyUser.objects.annotate(num_children=Count('children'))\
                         .annotate(
                            valid_registrations=Count(
                                Case(When(children__registrations__in=Registration.objects.validated(), then=1))
                            ),
                            waiting_registrations=Count(
                                Case(When(children__registrations__in=Registration.objects.waiting(), then=1))
                            ),
                            opened_bills=Count(
                                Case(When(bills__status=Bill.STATUS.waiting, then=1))
                            ),
                         )\
                         .prefetch_related('children')

    def post(self, request, *args, **kwargs):
        userids = list(set(json.loads(request.POST.get('data', '[]'))))
        self.request.session['mail-userids'] = userids
        return HttpResponseRedirect(reverse('backend:custom-mail-custom-users'))


class MailUsersView(BackendMixin, View):
    def post(self, request, *args, **kwargs):
        userids = list(set(json.loads(request.POST.get('data', '[]'))))
        self.request.session['mail-userids'] = userids
        params = ''
        if 'prev' in request.GET:
            params = '?prev=' + urlencode(request.GET.get('prev'))
        return HttpResponseRedirect(reverse('backend:custom-mail-custom-users') + params)


class UserExportView(BackendMixin, ExcelResponseMixin, View):
    filename = _("users")
    resource_class = UserResource


class ManagerMixin(object):
    @staticmethod
    def get_queryset():
        return Group.objects.get(name=MANAGERS_GROUP).user_set.all()


class ManagerListView(ManagerMixin, UserListView):
    template_name = 'backend/user/manager-list.html'


class ManagerExportView(BackendMixin, ExcelResponseMixin, ManagerMixin, View):
    filename = _("managers")
    resource_class = InstructorResource


class InstructorMixin(object):
    @staticmethod
    def get_queryset():
        return Group.objects.get(name=INSTRUCTORS_GROUP).user_set.all()


class InstructorListView(InstructorMixin, UserListView):
    template_name = 'backend/user/instructor-list.html'


class InstructorExportView(BackendMixin, ExcelResponseMixin, InstructorMixin, View):
    filename = _("instructors")
    resource_class = InstructorResource


class UserCreateView(BackendMixin, SuccessMessageMixin, CreateView):
    model = FamilyUser
    form_class = ManagerWithPasswordForm
    template_name = 'backend/user/create.html'
    success_url = reverse_lazy('backend:user-list')

    def form_valid(self, form):
        self.object = form.save()
        self.object.set_password(form.cleaned_data['password1'])
        self.object.save()
        self.object.is_manager = form.cleaned_data['is_manager']
        return super(UserCreateView, self).form_valid(form)

    def get_success_message(self, cleaned_data):
        return _("User %s has been added.") % self.object.full_name


class ManagerCreateView(UserCreateView):
    success_url = reverse_lazy('backend:manager-list')

    def get_context_data(self, **kwargs):
        ctx = super(ManagerCreateView, self).get_context_data(**kwargs)
        ctx['is_manager'] = True
        return ctx

    def get_initial(self):
        initial = super(ManagerCreateView, self).get_initial()
        initial['is_manager'] = True
        return initial

    def get_success_message(self, cleaned_data):
        return _("Manager %s has been added.") % self.object.full_name


class InstructorCreateView(UserCreateView):
    success_url = reverse_lazy('backend:instructor-list')
    form_class = InstructorWithPasswordForm

    def get_context_data(self, **kwargs):
        ctx = super(InstructorCreateView, self).get_context_data(**kwargs)
        ctx['is_instructor'] = True
        return ctx

    def form_valid(self, form):
        self.object = form.save()
        self.object.is_manager = form.cleaned_data['is_manager']
        self.object.is_instructor = True
        return super(InstructorCreateView, self).form_valid(form)

    def get_success_message(self, cleaned_data):
        return _("Instructor %s has been added.") % self.object.full_name


class UserUpdateView(BackendMixin, SuccessMessageMixin, UpdateView):
    model = FamilyUser
    template_name = 'backend/user/update.html'

    def get_initial(self):
        initial = super(UserUpdateView, self).get_initial()
        initial['is_manager'] = self.object.is_manager
        return initial

    def get_form_class(self):
        if self.object.is_instructor:
            return InstructorForm
        return ManagerForm

    def get_context_data(self, **kwargs):
        ctx = super(UserUpdateView, self).get_context_data(**kwargs)
        ctx['is_instructor'] = self.object.is_instructor
        return ctx

    def form_valid(self, form):
        self.object = form.save()
        self.object.is_manager = form.cleaned_data['is_manager']
        self.object.save()
        return super(UserUpdateView, self).form_valid(form)

    def get_success_url(self):
        if self.object.is_instructor:
            return reverse_lazy('backend:instructor-list')
        return reverse_lazy('backend:user-list')

    def get_success_message(self, cleaned_data):
        return _("Contact informations of %s have been updated.") % self.object.full_name


class UserDeleteView(BackendMixin, SuccessMessageMixin, DeleteView):
    model = FamilyUser
    template_name = 'backend/user/confirm_delete.html'
    success_url = reverse_lazy('backend:user-list')
    success_message = _("User has been deleted.")


class UserDetailView(BackendMixin, DetailView):
    model = FamilyUser
    template_name = 'backend/user/detail.html'


class InstructorDetailView(BackendMixin, DetailView):
    model = FamilyUser
    template_name = 'backend/user/detail-instructor.html'


class PasswordSetView(BackendMixin, SuccessMessageMixin, FormView):
    form_class = SetPasswordForm
    template_name = 'backend/user/password-change.html'

    def get_success_message(self, cleaned_data):
        return _("Password changed for user %s.") % self.get_object()

    def get_success_url(self):
        return self.get_object().get_backend_url()

    def get_object(self):
        user_id = self.kwargs.get('user', None)
        return get_object_or_404(FamilyUser, pk=user_id)

    def get_form_kwargs(self):
        kwargs = super(PasswordSetView, self).get_form_kwargs()
        kwargs['user'] = self.get_object()
        return kwargs

    def form_valid(self, form):
        user = self.get_object()
        user.set_password(form.cleaned_data['new_password1'])
        user.save()
        return super(PasswordSetView, self).form_valid(form)


class ChildView(BackendMixin, View):
    def get_context_data(self, **kwargs):
        context = super(ChildView, self).get_context_data(**kwargs)
        context['family'] = get_object_or_404(FamilyUser, pk=self.kwargs['user'])
        return context

    def get_success_url(self):
        user = get_object_or_404(FamilyUser, pk=self.kwargs['user'])
        return user.get_backend_url()


class ChildDetailView(BackendMixin, DetailView):
    model = Child
    template_name = 'backend/user/child-detail.html'
    pk_url_kwarg = 'child'
    slug_url_kwarg = 'lagapeo'
    slug_field = 'id_lagapeo'


class ChildListView(BackendMixin, ListView):
    model = Child
    template_name = 'backend/user/child-list.html'

    def get_queryset(self):
        return Child.objects.select_related('family', 'school_year')


class ChildCreateView(ChildView, SuccessMessageMixin, CreateView):
    model = Child
    form_class = ChildForm
    template_name = 'backend/user/child-create.html'
    success_message = _("User has been deleted.")

    def get_success_message(self, cleaned_data):
        return _("Child %s has been added.") % self.object.full_name

    def form_valid(self, form):
        user = get_object_or_404(FamilyUser, pk=self.kwargs['user'])
        child = form.save(commit=False)
        child.family = user
        child.save()
        return HttpResponseRedirect(self.get_success_url())


class ChildUpdateView(BackendMixin, SuccessMessageMixin, UpdateView):
    model = Child
    form_class = ChildForm
    template_name = 'backend/user/child-update.html'
    success_url = reverse_lazy('backend:child-list')
    pk_url_kwarg = 'child'

    def get_success_message(self, cleaned_data):
        return _("Child %s has been updated.") % self.object.full_name


class ChildAbsencesView(BackendMixin, DetailView):
    model = Child
    pk_url_kwarg = 'child'
    template_name = 'backend/user/absences.html'
    queryset = Child.objects.prefetch_related()

    def get_context_data(self, **kwargs):
        child = self.get_object()
        qs = Absence.objects.filter(child=child)\
                            .select_related('session', 'session__course', 'session__course__activity')\
                            .order_by('session__course__activity', 'session__course')
        kwargs['all_dates'] = list(set(qs.values_list('session__date', flat=True)))
        kwargs['all_dates'].sort()
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
        kwargs['activity_absences'] = activity_absences
        kwargs['course_absences'] = course_absences
        kwargs['levels'] = ChildActivityLevel.LEVELS

        return super(ChildAbsencesView, self).get_context_data(**kwargs)


class ChildDeleteView(BackendMixin, SuccessMessageMixin, DeleteView):
    model = Child
    template_name = 'backend/user/child-confirm_delete.html'
    success_url = reverse_lazy('backend:child-list')
    success_message = _("Child has been removed.")
    pk_url_kwarg = 'child'


class ChildImportView(BackendMixin, SuccessMessageMixin, FormView):
    form_class = ChildImportForm
    success_url = reverse_lazy('backend:user-list')
    success_message = _("Children are being imported")
    template_name = 'backend/user/child-import.html'

    def form_valid(self, form):
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        for chunk in self.request.FILES['thefile'].chunks():
            temp_file.write(chunk)
        temp_file.close()
        import_children.delay(temp_file.name,
                              tenant_id=self.request.tenant.pk,
                              user_id=self.request.user.pk)
        return super(ChildImportView, self).form_valid(form)
