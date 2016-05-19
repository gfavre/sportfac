import json

from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import Group
from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse_lazy, reverse
from django.db.models import Count, Case, When
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.views.generic import CreateView, DeleteView, DetailView, \
                                ListView, UpdateView, View, FormView

from backend import MANAGERS_GROUP, RESPONSIBLE_GROUP
from profiles.forms import (ManagerForm, ManagerWithPasswordForm, 
                            ResponsibleForm, ResponsibleWithPasswordForm)
from profiles.models import FamilyUser
from registrations.models import Bill, Child, Registration
from registrations.forms import ChildForm

from .mixins import BackendMixin

__all__ = ('UserListView', 'UserCreateView', 'PasswordSetView',
           'UserUpdateView', 'UserDeleteView', 'UserDetailView',
           'ChildCreateView', 'ChildUpdateView', 'ChildDeleteView',
            'ManagerListView', 'ManagerCreateView', 
            'ResponsibleListView', 'ResponsibleCreateView', 'ResponsibleDetailView'
           )

valid_registrations = Registration.objects.validated()

FamilyUser.objects.annotate(
    valid_registrations=Count(Case(When(children__registrations__in= Registration.objects.validated(), then=1))),
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
                                Case(When(children__registrations__in= Registration.objects.validated(), then=1))
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


class ManagerListView(UserListView):
    template_name = 'backend/user/manager-list.html'
    
    def get_queryset(self):
        return Group.objects.get(name=MANAGERS_GROUP).user_set.all()


class ResponsibleListView(UserListView):
    template_name = 'backend/user/responsible-list.html'
    
    def get_queryset(self):
        return Group.objects.get(name=RESPONSIBLE_GROUP).user_set.all()
    

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
    

class ResponsibleCreateView(UserCreateView):
    success_url = reverse_lazy('backend:responsible-list')
    form_class = ResponsibleWithPasswordForm
    
    def get_context_data(self, **kwargs):
        ctx = super(ResponsibleCreateView, self).get_context_data(**kwargs)
        ctx['is_responsible'] = True
        return ctx
    
    def form_valid(self, form):
        self.object = form.save()
        self.object.is_manager = form.cleaned_data['is_manager']
        self.object.is_responsible = True
        return super(ResponsibleCreateView, self).form_valid(form)
    
    def get_success_message(self, cleaned_data):
        return _("Responsible %s has been added.") % self.object.full_name
    

class UserUpdateView(BackendMixin, SuccessMessageMixin, UpdateView):
    model = FamilyUser
    template_name = 'backend/user/update.html'

    def get_initial(self):
        initial = super(UserUpdateView, self).get_initial()
        initial['is_manager'] = self.object.is_manager
        return initial

    def get_form_class(self):
        if self.object.is_responsible:
            return ResponsibleForm
        return ManagerForm
    
    def get_context_data(self, **kwargs):
        ctx = super(UserUpdateView, self).get_context_data(**kwargs)
        ctx['is_responsible'] = self.object.is_responsible
        return ctx

    def form_valid(self, form):
        self.object = form.save()
        self.object.is_manager = form.cleaned_data['is_manager']
        self.object.save()
        return super(UserUpdateView, self).form_valid(form)
       
    def get_success_url(self):
        if self.object.is_responsible:
            return reverse_lazy('backend:responsible-list')
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

class ResponsibleDetailView(BackendMixin, DetailView):
    model = FamilyUser
    template_name = 'backend/user/detail-responsible.html'


class PasswordSetView(BackendMixin, SuccessMessageMixin, FormView):
    form_class = SetPasswordForm
    template_name ='backend/user/password-change.html'
    
    def get_success_message(self, cleaned_data):
        return _("Password changed for user %s.") % self.get_object()
    
    def get_success_url(self):
        return self.get_object().get_backend_url()
    
    def get_object(self):
        user_id = self.kwargs.get('user', None)
        return get_object_or_404(FamilyUser, pk=user_id)
    
    def get_form_kwargs(self):
        kwargs = super(PasswordSetView, self).get_form_kwargs()
        user_id = self.request.GET.get('user', None)
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


class ChildUpdateView(ChildView, SuccessMessageMixin, UpdateView):
    model = Child
    form_class = ChildForm
    template_name = 'backend/user/child-update.html'

    def get_success_message(self, cleaned_data):
        return _("Child %s has been updated.") % self.object.full_name


class ChildDeleteView(ChildView, SuccessMessageMixin, DeleteView):
    model = Child
    template_name = 'backend/user/child-confirm_delete.html'
    success_message = _("Child has been removed.")
