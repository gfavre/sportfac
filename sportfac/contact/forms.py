# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from django.core.mail import EmailMessage
from django.conf import settings

import floppyforms as forms
from dynamic_preferences.registries import global_preferences_registry


class ContactForm(forms.Form):
    name = forms.CharField(label=_("Name"),
                           widget=forms.TextInput())
    email = forms.EmailField(label=_("E-mail"),
                             widget=forms.EmailInput(attrs={'placeholder': 'john@example.com',}))
    subject = forms.CharField(label=_("Subject"),
                              widget=forms.TextInput())

    message = forms.CharField(label=_("Message"),
                              widget=forms.Textarea(attrs={'rows': 5}))

    def send_mail(self, fail_silently=False):
        global_preferences = global_preferences_registry.manager()

        bcc = None
        if settings.KEPCHUP_SEND_COPY_CONTACT_MAIL_TO_ADMIN:
            bcc = ['%s <%s>' % (mail_tuple[0], mail_tuple[1]) for mail_tuple in settings.MANAGERS]

        email = EmailMessage(
            subject=u'%s [%s - formulaire de contact]' % (
                self.cleaned_data['subject'],
                global_preferences['email__SCHOOL_NAME'].decode('utf-8')),
            body=u'%s <%s> a utilisé le formulaire de contact.\n\n %s' % (
                self.cleaned_data['name'],
                self.cleaned_data['email'],
                self.cleaned_data['message']),
            from_email=global_preferences['email__FROM_MAIL'].decode('utf-8'),
            to=[global_preferences['email__CONTACT_MAIL'].decode('utf-8')],
            bcc=bcc,
            reply_to=['%s <%s>' % (self.cleaned_data['name'], self.cleaned_data['email'])]
        )
        email.send(fail_silently=fail_silently)
