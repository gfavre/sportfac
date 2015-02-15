import json

from django.contrib.auth.models import Group
from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse_lazy, reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.views.generic import CreateView, DeleteView, DetailView, \
                                ListView, UpdateView, View

from backend import MANAGERS_GROUP, RESPONSIBLE_GROUP
from profiles.models import FamilyUser, Child
from profiles.forms import UserForm, UserUpdateForm, UserPayForm, ChildForm
from .mixins import BackendMixin

__all__ = ('UserListView', 'UserCreateView', 
           'UserUpdateView', 'UserPayUpdateView', 'UserDeleteView', 'UserDetailView',
           'ChildCreateView', 'ChildUpdateView', 'ChildDeleteView',
            'ManagerListView', 'ManagerCreateView', 'ResponsibleListView'
           )


class UserListView(BackendMixin, ListView):
    model = FamilyUser
    queryset = FamilyUser.objects.prefetch_related('children')
    template_name = 'backend/user/list.html'

    def post(self, request, *args, **kwargs):
        userids = list(set(json.loads(request.POST.get('data', '[]'))))
        self.request.session['mail-userids'] = userids
        return HttpResponseRedirect(reverse('backend:custom-mail-custom-users')) 


class ManagerListView(UserListView):
    queryset =  Group.objects.get(name=MANAGERS_GROUP).user_set.all()
    template_name = 'backend/user/manager-list.html'


class ResponsibleListView(UserListView):
    queryset =  Group.objects.get(name=RESPONSIBLE_GROUP).user_set.all()
    template_name = 'backend/user/manager-list.html'


class UserCreateView(BackendMixin, SuccessMessageMixin, CreateView):
    model = FamilyUser
    form_class = UserForm
    template_name = 'backend/user/create.html'
    success_url = reverse_lazy('backend:user-list')    

    def form_valid(self, form):
        self.object = form.save()
        self.object.set_password(form.cleaned_data['password'])
        self.object.is_manager = form.cleaned_data['is_manager']
        return super(UserCreateView, self).form_valid(form)

    def get_success_message(self, cleaned_data):
        return _("User %s has been added.") % self.object.full_name


class ManagerCreateView(UserCreateView):
    success_url = reverse_lazy('backend:manager-list')    

    def get_initial(self):
        initial = super(ManagerCreateView, self).get_initial()
        initial['is_manager'] = True
        return initial

    def get_success_message(self, cleaned_data):
        return _("Manager %s has been added.") % self.object.full_name


class UserUpdateView(BackendMixin, SuccessMessageMixin, UpdateView):
    model = FamilyUser
    form_class = UserUpdateForm
    template_name = 'backend/user/update.html'
    success_url = reverse_lazy('backend:user-list')    

    def form_valid(self, form):
        self.object = form.save()
        self.object.is_manager = form.cleaned_data['is_manager']
        return super(UserUpdateView, self).form_valid(form)

    def get_success_message(self, cleaned_data):
        return _("Contact informations of %s have been updated.") % self.object.full_name


class UserPayUpdateView(BackendMixin, SuccessMessageMixin, UpdateView):
    model = FamilyUser
    form_class = UserPayForm
    template_name = 'backend/user/pay.html'
    success_url = reverse_lazy('backend:user-list')    
    
    def get_success_message(self, cleaned_data):
        return _("Status of %s has been changed.") % self.object.full_name


class UserDeleteView(BackendMixin, SuccessMessageMixin, DeleteView):
    model = FamilyUser
    template_name = 'backend/user/confirm_delete.html'
    success_url = reverse_lazy('backend:user-list')    
    success_message = _("User has been deleted.")


class UserDetailView(BackendMixin, DetailView):
    model = FamilyUser
    template_name = 'backend/user/detail.html'


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
