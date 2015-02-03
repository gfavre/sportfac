import json

from django.core.urlresolvers import reverse_lazy, reverse
from django.http import HttpResponseRedirect
from django.views.generic import CreateView, DeleteView, DetailView, \
                                ListView, UpdateView

from profiles.models import FamilyUser
from profiles.forms import UserForm, UserUpdateForm

from .mixins import BackendMixin

__all__ = ('UserListView', 'UserCreateView', 'UserUpdateView', 'UserDeleteView', 'UserDetailView')

class UserListView(BackendMixin, ListView):
    model = FamilyUser
    queryset = FamilyUser.objects.prefetch_related('children')
    template_name = 'backend/user/list.html'
        
    def post(self, request, *args, **kwargs):
        post = request.POST
        userids = list(set(json.loads(request.POST.get('data', '[]'))))
        self.request.session['mail-userids'] = userids
        return HttpResponseRedirect(reverse('backend:custom-mail-custom-users')) 

class UserCreateView(BackendMixin, CreateView):
    model = FamilyUser
    form_class = UserForm
    template_name = 'backend/user/create.html'
    success_url = reverse_lazy('backend:user-list')    

    def form_valid(self, form):
        self.object = form.save()
        self.object.set_password(form.cleaned_data['password'])
        self.object.is_manager = form.cleaned_data['is_manager']
        return super(UserCreateView, self).form_valid(form)

class UserUpdateView(BackendMixin, UpdateView):
    model = FamilyUser
    form_class = UserUpdateForm
    template_name = 'backend/user/update.html'
    success_url = reverse_lazy('backend:user-list')    

    def form_valid(self, form):
        self.object = form.save()
        self.object.is_manager = form.cleaned_data['is_manager']
        return super(UserUpdateView, self).form_valid(form)

class UserDeleteView(BackendMixin, DeleteView):
    model = FamilyUser
    template_name = 'backend/user/confirm_delete.html'
    success_url = reverse_lazy('backend:user-list')    
    

class UserDetailView(BackendMixin, DetailView):
    model = FamilyUser
    template_name = 'backend/user/detail.html'
