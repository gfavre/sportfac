from django.utils.translation import ugettext as _

from multiupload.fields import MultiFileField

import floppyforms.__future__ as forms


class MailForm(forms.Form):
    subject = forms.CharField(label=_("Subject"), max_length=255)
    message = forms.CharField(label=_("Message"), widget=forms.Textarea)
    attachments = MultiFileField(label=_("Attachments"), min_num=0, max_file_size=1024*1024*5, required=False)


class PreviewForm(forms.Form):
    pass
