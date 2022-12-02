from __future__ import unicode_literals

from __future__ import absolute_import
from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class SchoolsConfig(AppConfig):
    name = 'schools'
    verbose_name = _("Schools")