import json

from django.core.urlresolvers import reverse_lazy, reverse
from django.http import HttpResponseRedirect
from django.views.generic import CreateView, DeleteView, DetailView, \
                                ListView, UpdateView

from profiles.models import FamilyUser

from .mixins import BackendMixin

__all__ = ['UserListView',]

class UserListView(BackendMixin, ListView):
    model = FamilyUser
    queryset = FamilyUser.objects.prefetch_related('children')
    template_name = 'backend/user/list.html'
        
    def post(self, request, *args, **kwargs):
        post = request.POST
        userids = list(set(json.loads(request.POST.get('data', '[]'))))
        self.request.session['mail-userids'] = userids
        return HttpResponseRedirect(reverse('backend:custom-mail-custom-users')) 



#class ActivityDetailView(BackendMixin, DetailView):
#    model = Activity
#    template_name = 'backend/activity/detail.html'
#

#   
#
#class ActivityCreateView(BackendMixin, CreateView):
#    model = Activity
#    form_class = ActivityForm
#    template_name = 'backend/activity/create.html'
#
#class ActivityUpdateView(BackendMixin, UpdateView):
#    model = Activity
#    form_class = ActivityForm
#    template_name = 'backend/activity/update.html'
#    
#class ActivityDeleteView(BackendMixin, DeleteView):
#    model = Activity
#    template_name = 'backend/activity/confirm_delete.html'
#    success_url = reverse_lazy('backend:activity-list')