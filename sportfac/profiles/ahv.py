from __future__ import absolute_import

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

import floppyforms.__future__ as forms


class AHVValidator(object):
    """A validator for AHV number"""

    @staticmethod
    def ahv_checksum(value):
        """Calculate the EAN check digit for 13-digit numbers. The number passed
        should not have the check bit included."""
        return str(
            (10 - sum((3 - 2 * (i % 2)) * int(n) for i, n in enumerate(reversed(value)))) % 10
        )

    def __call__(self, value):
        """
        Validates the AHV value
        """
        if value is None:
            return value

        value = value.replace(" ", "").replace(".", "")
        if not value.isdigit():
            raise ValidationError(_("AHV must contain numbers only"))
        if len(value) != 13:
            raise ValidationError(_("AHV must be 13 numbers long."))

        if self.ahv_checksum(value[:-1]) != value[-1]:
            raise ValidationError(_("Not a valid AHV number."))


class AHVFormField(forms.CharField):
    """
    An AHV number consists of 11 numbers.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("min_length", 13)
        kwargs.setdefault("max_length", 16)
        self.default_validators = [AHVValidator()]
        super(AHVFormField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        value = super(AHVFormField, self).to_python(value)
        return value.upper().replace(" ", "").replace(".", "")

    def prepare_value(self, value):
        """The display format for AHV is ###.####.####.##"""
        if value is None:
            return value
        value = value.replace(" ", "").replace(".", "")
        if value:
            return "%s.%s.%s.%s" % (value[0:3], value[3:7], value[7:11], value[11:])
        return value


class AHVField(models.CharField):
    """An AHV number (French: AVS) consists of 13 numbers."""

    description = _("AHV number")

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 16)
        super(AHVField, self).__init__(*args, **kwargs)
        self.validators.append(AHVValidator())

    def to_python(self, value):
        value = super(AHVField, self).to_python(value)
        if value is not None:
            return value.replace(" ", "").replace(".", "")
        return value

    def formfield(self, **kwargs):
        defaults = {"form_class": AHVFormField}
        defaults.update(kwargs)
        return super(AHVField, self).formfield(**defaults)
