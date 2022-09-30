from django import forms
from django.utils.translation import ugettext_lazy as _


class WaitingSlotTransformForm(forms.Form):
    send_confirmation = forms.BooleanField(required=False, initial=True, label=_("Send confirmation email?"))
