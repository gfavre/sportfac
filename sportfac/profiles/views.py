from django.views.generic import ListView, CreateView, UpdateView
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.utils.translation import ugettext as _
from django.http import HttpResponseRedirect

from braces.views import LoginRequiredMixin
from registration.backends.simple.views import RegistrationView as BaseRegistrationView
from registration.compat import User
from registration import signals

from .models import FamilyUser, Child
from .forms import RegistrationForm, ContactInformationForm


class ChildrenListView(LoginRequiredMixin, ListView):
    template_name = 'profiles/children_list.html'
    context_object_name = 'children'
    
    def get_queryset(self):
        return Child.objects.filter(family = self.request.user).order_by('first_name')
        

class AccountView(LoginRequiredMixin, UpdateView):
    model = FamilyUser
    form_class = ContactInformationForm
    
    def get_object(self, queryset=None):
        return self.request.user    
    
class MyRegistrationView(BaseRegistrationView):
    """
    A registration backend which implements the simplest possible
    workflow: a user supplies a username, email address and password
    (the bare minimum for a useful account), and is immediately signed
    up and logged in).
    """
    form_class = RegistrationForm
    
    def get_success_url(self, request=None, user=None):
        # We need to be able to use the request and the new user when
        # constructing success_url.
        return '/'

    def register(self, request, **cleaned_data):
        email, password = cleaned_data['email'], cleaned_data['password1']
        first_name, last_name = cleaned_data['first_name'], cleaned_data['last_name']
        address, zipcode, city = cleaned_data['address'], cleaned_data['zipcode'], cleaned_data['city']
        private_phone, private_phone2 = cleaned_data['private_phone'], cleaned_data['private_phone2']
        
        FamilyUser.objects.create_user(email=email, password=password, 
                                         first_name=first_name, last_name=last_name,
                                         address=address, zipcode=zipcode, city=city,
                                         private_phone=private_phone, private_phone2=private_phone2)
        new_user = authenticate(email=email, password=password)
        login(request, new_user)
        signals.user_registered.send(sender=self.__class__,
                                     user=new_user,
                                     request=request)
        return new_user