from django.db import models
from django.utils.translation import gettext as _
from django.contrib.auth.models import AbstractUser

from activities.models import SCHOOL_YEARS


class TimeStampedModel(models.Model):
      """
      An abstract base class model that provides self-
      updating ``created`` and ``modified`` fields.
      """
      created = models.DateTimeField(auto_now_add=True)
      modified = models.DateTimeField(auto_now=True)
      class Meta:
          abstract = True


class FamilyUser(AbstractUser):
    address = models.TextField(_("Street"), blank = True)
    zipcode = models.PositiveIntegerField(_("NPA"))
    city = models.CharField(_('City'), max_length=100)
    country = models.CharField(_('Country'), max_length = 100, default=_("Switzerland"))
    private_phone = models.CharField(max_length=12)


# Create your models here.
class Child(TimeStampedModel):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    sex = models.CharField(max_length=1, choices=(('M', _('Male')), ('F', _('Female'))))
    birth_date = models.DateField()
    school_year = models.ForeignKey('SchoolYear')
    teacher = models.ForeignKey('Teacher')
    

class SchoolYear(models.Model):
    year = models.PositiveIntegerField(choices=SCHOOL_YEARS, unique=True)


class Teacher(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    years = models.ManyToManyField('SchoolYear')
