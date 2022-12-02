from __future__ import unicode_literals

from __future__ import absolute_import
from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class ProfilesConfig(AppConfig):
    name = 'profiles'
    verbose_name = _("Users")