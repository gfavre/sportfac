from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SchoolsConfig(AppConfig):
    name = "schools"
    verbose_name = _("Schools")
