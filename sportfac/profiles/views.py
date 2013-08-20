from django.views.generic import ListView, UpdateView, TemplateView, FormView
from django.contrib.auth import authenticate, login
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse_lazy
from django.db.models import Sum

from braces.views import LoginRequiredMixin
from registration.backends.simple.views import RegistrationView as BaseRegistrationView
#from registration.compat import User
from registration import signals

from .models import FamilyUser, Child, Registration
from .forms import RegistrationForm, ContactInformationForm, AcceptTermsForm


class ChildrenListView(LoginRequiredMixin, ListView):
    template_name = 'profiles/children_list.html'
    context_object_name = 'children'
    
    def get_queryset(self):
        return Child.objects.filter(family = self.request.user).order_by('first_name')
        

class AccountView(LoginRequiredMixin, UpdateView):
    model = FamilyUser
    form_class = ContactInformationForm
    success_url = reverse_lazy('profiles_children')
    
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
        return 'profiles_children'
    
    def register(self, request, **cleaned_data):
        email, password = cleaned_data['email'], cleaned_data['password1']
        first_name, last_name = cleaned_data['first_name'], cleaned_data['last_name']
        address, zipcode, city = cleaned_data['address'], cleaned_data['zipcode'], cleaned_data['city']
        private_phone, private_phone2 = cleaned_data['private_phone'], cleaned_data['private_phone2']
        private_phone3 = cleaned_data['private_phone3']
        
        
        FamilyUser.objects.create_user(email=email, password=password, 
                                       first_name=first_name, last_name=last_name,
                                       address=address, zipcode=zipcode, city=city,
                                       private_phone=private_phone,
                                       private_phone2=private_phone2,
                                       private_phone3=private_phone3)
        new_user = authenticate(email=email, password=password)
        login(request, new_user)
        signals.user_registered.send(sender=self.__class__,
                                     user=new_user,
                                     request=request)
        return new_user

      

class RegisteredActivitiesListView(LoginRequiredMixin, FormView):
    model = Registration
    form_class = AcceptTermsForm
    success_url = reverse_lazy('profiles_billing')
    template_name = 'profiles/registration_list.html'
    
    def get_queryset(self):
        return Registration.objects.select_related('extra_infos',
                                                   'child', 
                                                   'course', 'course__activity').prefetch_related('extra_infos').filter(child__in=self.request.user.children.all())
    
    
    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context        
        context = super(RegisteredActivitiesListView, self).get_context_data(**kwargs)
        context['registered_list'] = self.get_queryset()
        
        
        registrations = context['registered_list'].order_by('course__start_date', 
                                                                   'course__end_date')
        context['total_price'] = registrations.aggregate(Sum('course__price'))['course__price__sum']
        
                    
        context['overlaps'] = []
        context['overlapped'] = set()
        for (idx, registration) in list(enumerate(registrations))[:-1]:
            for registration2 in registrations[idx+1:]:
                if registration.overlap(registration2):
                    context['overlaps'].append((registration, registration2))
                    context['overlapped'].add(registration.id)
                    context['overlapped'].add(registration2.id)
        
        
        return context

    def form_valid(self, form):
        for registration in self.get_queryset().all():
            registration.validated = True
            registration.save()
        self.request.user.finished_registration = True
        self.request.user.save()
        return super(RegisteredActivitiesListView, self).form_valid(form)
    

class BillingView(LoginRequiredMixin, TemplateView):
    template_name = "profiles/billing.html"
    
    def get_context_data(self, **kwargs):
        context = super(BillingView, self).get_context_data(**kwargs)
        registrations = Registration.objects.filter(child__in=self.request.user.children.all(), validated=True, paid=False)
        total = registrations.aggregate(Sum('course__price')).get('course__price__sum')
        context['total'] = total or 0
        
        return context
