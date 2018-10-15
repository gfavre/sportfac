# -*- coding: utf-8 -*-
from django.utils.translation import ugettext as _
from multiupload.fields import MultiFileField

import floppyforms.__future__ as forms


class MailForm(forms.Form):
    subject = forms.CharField(label=_("Subject"), max_length=255)
    message = forms.CharField(label=_("Message"), widget=forms.Textarea)
    attachments = MultiFileField(label=_("Attachments"), min_num=0, max_file_size=1024*1024*5, required=False)
    send_copy = forms.BooleanField(label=_("Send me a copy"), initial=True, required=False)


class CopiesForm(forms.Form):
    send_copy = forms.BooleanField(label=_("Send me a copy"), initial=True, required=False)
    copy_all_admins = forms.BooleanField(label=_("Send a copy to all other administrators"), required=False)


class InstructorCopiesForm(forms.Form):
    copy_all_instructors = forms.BooleanField(label=_("Send a copy to all other instructors"),
                                              initial=False, required=False)


class CourseMailForm(MailForm):
    copy_all_instructors = forms.BooleanField(label=_("Send a copy to all other instructors"),
                                              initial=True, required=False)


class AdminMailForm(MailForm):
    copy_all_admins = forms.BooleanField(label=_("Send a copy to all other administrators"),
                                         initial=False, required=False)


class PreviewForm(forms.Form):
    pass
