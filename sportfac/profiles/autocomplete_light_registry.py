from django.utils.translation import ugettext as _

import autocomplete_light

from .models import Child



class ChildAutoComplete(autocomplete_light.AutocompleteModelBase):
    search_fields=['^first_name', 'last_name']
    autocomplete_js_attributes={'placeholder': _('Child name'),}
    
    def choices_for_request(self):
        choices = super(ChildAutoComplete, self).choices_for_request()
        if not self.request.user.is_staff:
            choices = []
        return choices

autocomplete_light.register(Child, ChildAutoComplete)
