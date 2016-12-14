from django.utils.translation import ugettext_lazy as _

from import_export import fields, resources, widgets

from backend.templatetags.switzerland import phone, iban, ahv
from .models import FamilyUser


class PhoneWidget(widgets.Widget):
    def render(self, value, obj=None):
        return phone(value)

class AHVWidget(widgets.Widget):
    def render(self, value, obj=None):
        return ahv(value)

class IBANWidget(widgets.Widget):
    def render(self, value, obj=None):
        return iban(value)

class UserResource(resources.ModelResource):
    first_name = fields.Field(attribute='first_name', column_name=_("First name"))
    last_name = fields.Field(attribute='last_name', column_name=_("Last name"))
    address = fields.Field(attribute='address', column_name=_("Street"))
    zipcode = fields.Field(attribute='zipcode', column_name=_("NPA"))
    city = fields.Field(attribute='city', column_name=_("City"))
    country = fields.Field(attribute='country', column_name=_("Country"))
    home_phone = fields.Field(attribute='private_phone',
                              column_name=_("Home phone"),
                              widget=PhoneWidget())
    mobile_phone = fields.Field(attribute='private_phone2',
                                column_name=_("Mobile phone"),
                                widget=PhoneWidget())
    other_phone = fields.Field(attribute='private_phone3',
                               column_name=_("Other phone"),
                               widget=PhoneWidget())

    class Meta:
        model = FamilyUser
        fields = ('id', 'first_name', 'last_name', 'address', 'zipcode', 'city', 'country',
                  'home_phone', 'mobile_phone', 'other_phone')
        export_order = fields


class InstructorResource(UserResource):
    iban = fields.Field(attribute='iban', column_name=_("IBAN"), widget=IBANWidget())
    birth_date = fields.Field(attribute='birth_date', column_name=_("Birth date"))
    ahv = fields.Field(attribute='ahv', column_name=_('AHV number'), widget=AHVWidget())

    class Meta:
        model = FamilyUser
        fields = ('id', 'first_name', 'last_name', 'address', 'zipcode', 'city', 'country',
                  'home_phone', 'mobile_phone', 'other_phone', 'iban', 'birth_date', 'ahv')
        export_order = fields