import json

from django.core.urlresolvers import reverse_lazy, reverse
from django.http import HttpResponseRedirect
from django.views.generic import CreateView, DeleteView, DetailView, \
                                ListView, UpdateView, View
from django.shortcuts import get_object_or_404

from profiles.models import FamilyUser, Child
from profiles.forms import UserForm, UserUpdateForm, ChildForm

from .mixins import BackendMixin

__all__ = ('UserListView', 'UserCreateView', 'UserUpdateView', 'UserDeleteView', 'UserDetailView',
           'ChildCreateView', 'ChildUpdateView', 'ChildDeleteView')

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


class ChildView(BackendMixin, View):
    def get_context_data(self, **kwargs):
        context = super(ChildView, self).get_context_data(**kwargs)
        context['family'] = get_object_or_404(FamilyUser, pk=self.kwargs['user'])
        return context
       
    def get_success_url(self):
        user = get_object_or_404(FamilyUser, pk=self.kwargs['user'])
        return user.get_backend_url()
    


class ChildCreateView(ChildView, CreateView):
    model = Child
    form_class = ChildForm
    template_name = 'backend/user/child-create.html'
    
    
    def form_valid(self, form):
        user = get_object_or_404(FamilyUser, pk=self.kwargs['user'])
        child = form.save(commit=False)
        child.family = user
        child.save()
        return HttpResponseRedirect(self.get_success_url())
        

class ChildUpdateView(ChildView, UpdateView):
    model = Child
    form_class = ChildForm
    template_name = 'backend/user/child-update.html'
        

class ChildDeleteView(ChildView, DeleteView):
    model = Child
    template_name = 'backend/user/child-confirm_delete.html'
    