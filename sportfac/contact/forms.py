# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from django.core.mail import send_mail
from django.conf import settings

import floppyforms as forms


class ContactForm(forms.Form):
    name = forms.CharField(label=_("Name"),
                           widget=forms.TextInput())
    email = forms.EmailField(label=_("E-mail"), 
                             widget=forms.EmailInput(attrs={'placeholder': 'john@example.com',}))
    subject = forms.CharField(label=_("Subject"),
                           widget=forms.TextInput())

    message = forms.CharField(label=_("Message"), 
                              widget=forms.Textarea())
    
    def send_mail(self, fail_silently=False):
        message_dict = {'from_email': settings.DEFAULT_FROM_EMAIL,
                        'message': u'%s <%s> a utilisé le formulaire de contact.\n\n %s' % (
                            self.cleaned_data['name'],
                            self.cleaned_data['email'],
                            self.cleaned_data['message']),
                        'recipient_list': [mail_tuple[1] for mail_tuple in settings.MANAGERS],
                        'subject': self.cleaned_data['subject'] + ' [sportfac - formulaire de contact]'}
        send_mail(fail_silently=fail_silently, **message_dict)
    