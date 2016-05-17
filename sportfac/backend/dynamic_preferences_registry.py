from datetime import datetime, timedelta
import dateutil.parser

from django import forms
from django.utils import timezone

from dynamic_preferences.types import BaseSerializer
from dynamic_preferences.types import (BasePreferenceType, BooleanPreference, 
                                       IntegerPreference, LongStringPreference, 
                                       StringPreference, Section)
from dynamic_preferences.registries import PerInstancePreferenceRegistry, global_preferences_registry, preference_models

from .models import TenantPreferenceModel


class TenantRegistry(PerInstancePreferenceRegistry):
    preference_model = TenantPreferenceModel

tenant_preferences_registry = TenantRegistry()
preference_models.register(TenantPreferenceModel, tenant_preferences_registry)



email = Section('email')
phase = Section('phase')

class DateTimeSerializer(BaseSerializer):
    @classmethod
    def clean_to_db_value(cls, value):
        if not isinstance(value, datetime):
            raise cls.exception('DateTimeSerializer can only serialize datetime objects')
        return value.isoformat()

    @classmethod
    def to_python(cls, value, **kwargs):
        try:
            return dateutil.parser.parse(value)
        except:
            raise cls.exception("Value {0} cannot be converted to datetime")


class DateTimePreference(BasePreferenceType):
    field_class = forms.DateTimeField
    serializer = DateTimeSerializer


@global_preferences_registry.register
class FromMail(StringPreference):
    section = email
    name = 'FROM_MAIL'
    default = 'info@kepchup.ch'

@global_preferences_registry.register
class ReplyToMail(StringPreference):
    section = email
    name = 'REPLY_TO_MAIL'
    default = 'info@kepchup.ch'


@global_preferences_registry.register
class SchoolName(StringPreference):
    section = email
    name = 'SCHOOL_NAME'
    default = 'Sport scolaire facultatif'


@global_preferences_registry.register
class Signature(LongStringPreference):
    section = email
    name = 'SIGNATURE'
    default = """Sport scolaire facultatif
info@kepchup.ch"""


@tenant_preferences_registry.register
class StartRegistration(DateTimePreference):
    section = phase
    name = 'START_REGISTRATION'
    default = timezone.now() + timedelta(days=30)


@tenant_preferences_registry.register
class EndRegistration(DateTimePreference):
    section = phase
    name = 'END_REGISTRATION'
    default = timezone.now() + timedelta(days=60)


@tenant_preferences_registry.register
class CurrentPhase(IntegerPreference):
    section = phase
    name = 'CURRENT_PHASE'
    default = 1


@global_preferences_registry.register
class MaintenanceMode(BooleanPreference):
    name = 'maintenance_mode'
    default = False