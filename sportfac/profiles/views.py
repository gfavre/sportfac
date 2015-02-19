from django.views.generic import ListView, UpdateView, TemplateView, FormView
from django.contrib.auth import authenticate, login
from django.contrib.auth.views import password_change as auth_password_change
import django.contrib.auth.views as auth_views
from django.contrib.messages.views import SuccessMessageMixin
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse_lazy, reverse
from django.db.models import Sum

from braces.views import LoginRequiredMixin
from registration.backends.simple.views import RegistrationView as BaseRegistrationView
from registration import signals

from .models import FamilyUser, Child, Registration
from .forms import *

from sportfac.views import WizardMixin

__all__ = ('password_change', 'password_reset', 
           'AccountView', 'BillingView', 'ChildrenListView', 
           'RegisteredActivitiesListView', 'RegistrationView', 'SummaryView',
           'WizardAccountView', 'WizardBillingView', 'WizardChildrenListView', 
           'WizardRegistrationView')

def password_change(request):
    "Wrap the built-in password reset view and pass it the arguments"
    return auth_views.password_change(request, password_change_form=PasswordChangeForm)

def password_reset(request):
    "Wrap the built-in password reset view and pass it the arguments"
    return auth_views.password_reset(request, password_reset_form=PasswordResetForm)


class ChildrenListView(LoginRequiredMixin, ListView):
    template_name = 'profiles/children.html'
    context_object_name = 'children'
    
    def get_queryset(self):
        return Child.objects.filter(family = self.request.user).order_by('first_name')
        
class WizardChildrenListView(WizardMixin, ChildrenListView):
    template_name = 'profiles/wizard_children.html'



class _BaseAccount(LoginRequiredMixin, UpdateView):
    model = FamilyUser
    form_class = ContactInformationForm
    def get_object(self, queryset=None):
        return self.request.user
    

class AccountView(SuccessMessageMixin, _BaseAccount):
    template_name = 'profiles/account.html'
    success_message = _('Contact informations have been saved.')

class WizardAccountView(WizardMixin, _BaseAccount):
    template_name = 'profiles/wizard_account.html'
    success_url = reverse_lazy('wizard_children')
    

class RegistrationView(BaseRegistrationView):
    """
    A registration backend which implements the simplest possible
    workflow: a user supplies a username, email address and password
    (the bare minimum for a useful account), and is immediately signed
    up and logged in).
    """
    form_class = RegistrationForm
    success_url = reverse_lazy('profiles_children')
        
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


class WizardRegistrationView(WizardMixin, RegistrationView):
    template_name = 'registration/wizard_registration.html'

    success_url = reverse_lazy('wizard_children')


class RegisteredActivitiesListView(LoginRequiredMixin, WizardMixin, FormView):
    model = Registration
    form_class = AcceptTermsForm
    success_url = reverse_lazy('wizard_billing')
    template_name = 'profiles/registration_list.html'
    
    def get_queryset(self):
        return Registration.objects\
                           .select_related('extra_infos',
                                           'child', 
                                           'course',
                                           'course__activity')\
                           .prefetch_related('extra_infos')\
                           .filter(child__in=self.request.user.children.all())
    
    
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
            registration.set_valid()
            registration.save()
        self.request.user.finished_registration = True
        self.request.user.update_total()
        self.request.user.save()
        return super(RegisteredActivitiesListView, self).form_valid(form)
    

class BillingView(LoginRequiredMixin, TemplateView):
    template_name = "profiles/billing.html"
    
    def get_context_data(self, **kwargs):
        context = super(BillingView, self).get_context_data(**kwargs)
        registrations = Registration.objects.validated().filter(
                            child__in=self.request.user.children.all())
        context['registered_list'] = registrations.all()
        total = registrations.aggregate(Sum('course__price')).get('course__price__sum')
        context['total_price'] = total or 0
        self.request.user.update_total()
        self.request.user.save()
        
        return context

class SummaryView(BillingView):
    template_name = "profiles/summary.html"

class WizardBillingView(WizardMixin, BillingView):
    template_name = "profiles/wizard_billing.html"

