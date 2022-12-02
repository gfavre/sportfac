# -*- coding: utf-8 -*-
from __future__ import absolute_import
from django.views.generic.edit import FormView
from django.urls import reverse_lazy

from .forms import ContactForm


class ContactView(FormView):
    template_name = 'contact/contact.html'
    form_class = ContactForm
    success_url = reverse_lazy('contact_thanks')

    def get_initial(self):
        initial = self.initial.copy()
        if self.request.user.is_authenticated():
            initial['name'] = self.request.user.full_name
            initial['email'] = self.request.user.email
        return initial

    def form_valid(self, form):
        form.send_mail()
        return super(ContactView, self).form_valid(form)
