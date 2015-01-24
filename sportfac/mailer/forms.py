from django.utils.translation import ugettext as _

import floppyforms.__future__ as forms


class MailForm(forms.Form):
    subject = forms.CharField(max_length=255)    
    message =  forms.CharField(widget=forms.Textarea)
    
class PreviewForm(forms.Form):
    pass