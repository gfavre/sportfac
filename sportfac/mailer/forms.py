from django.utils.translation import ugettext as _

import floppyforms.__future__ as forms


class MailForm(forms.Form):
    subject = forms.CharField(label=_("Subject"), max_length=255)    
    message =  forms.CharField(label=_("Message"), widget=forms.Textarea)
    
class PreviewForm(forms.Form):
    pass