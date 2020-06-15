# -*- coding: utf-8 -*-
import re

from django.db import models
from django.contrib.auth.models import Group
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from model_utils import Choices
from localflavor.generic.models import IBANField
from localflavor.generic.countries.sepa import IBAN_SEPA_COUNTRIES
from phonenumber_field.modelfields import PhoneNumberField

from activities.models import SCHOOL_YEARS
from backend import MANAGERS_GROUP, INSTRUCTORS_GROUP
from registrations.models import Registration, Bill
from .ahv import AHVField


class FamilyManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, zipcode, city, password=None, **extra_fields):
        """
        Creates and saves a User with the given email, favorite topping, and password.
        """
        if not email:
            msg = "Users must have an email address"
            raise ValueError(msg)
        if not first_name:
            msg = "Users must have a first name"
            raise ValueError(msg)
        if not last_name:
            msg = "Users must have a first name"
            raise ValueError(msg)
        if not zipcode:
            msg = "Users must have a zip"
            raise ValueError(msg)
        if not city:
            msg = "Users must have a city"
            raise ValueError(msg)

        user = self.model(
            email=FamilyManager.normalize_email(email),
            first_name=first_name,
            last_name=last_name,
            zipcode=zipcode,
            city=city,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, last_name, zipcode, city, password, **extra_fields):
        """
        Creates and saves a superuser with the given email, favorite topping and password.
        """
        user = self.create_user(email=email, first_name=first_name, last_name=last_name,
                                zipcode=zipcode, city=city, password=password, **extra_fields)
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class ActiveFamilyManager(FamilyManager):
    def get_queryset(self):
        return super(ActiveFamilyManager, self).get_queryset().filter(is_active=True)


class InstructorFamilyUserManager(ActiveFamilyManager):
    def get_queryset(self):
        return super(InstructorFamilyUserManager, self).get_queryset().filter(groups__name=INSTRUCTORS_GROUP)


class ManagerFamilyUserManager(ActiveFamilyManager):
    def get_queryset(self):
        return super(ManagerFamilyUserManager, self).get_queryset().filter(groups__name=MANAGERS_GROUP)


class FamilyUser(PermissionsMixin, AbstractBaseUser):
    COUNTRY = Choices(('CH', _("Switzerland")),
                       ('FL', _("Liechtenstein")),
                       ('D', _("Germany")),
                       ('F', _("France")),
                       ('I', _("Italy")),
                       ('A', _("Austria")))
    email = models.EmailField(verbose_name=_('Email address'), max_length=255, unique=True, db_index=True)
    first_name = models.CharField(_('First name'), max_length=30, blank=True)
    last_name = models.CharField(_('Last name'), max_length=30, blank=True)
    address = models.TextField(_("Street"), blank=True)
    zipcode = models.CharField(_("NPA"), blank=True, max_length=5)
    city = models.CharField(_('City'), max_length=100, blank=True)
    country = models.CharField(_('Country'), max_length=2, choices=COUNTRY, default=COUNTRY.CH)
    private_phone = PhoneNumberField(_("Home phone"), max_length=30, blank=True)
    private_phone2 = PhoneNumberField(_("Mobile phone"), max_length=30, blank=True)
    private_phone3 = PhoneNumberField(_("Other phone"), max_length=30, blank=True)
    iban = IBANField(include_countries=IBAN_SEPA_COUNTRIES, blank=True)
    birth_date = models.DateField(_("Birth date"), null=True, blank=True)
    ahv = AHVField(_('AHV number'),
                   help_text=_("New AHV number, e.g. 756.1234.5678.90"),
                   blank=True)
    js_identifier = models.CharField(_("J+S identifier"), max_length=30, blank=True)
    is_active = models.BooleanField(default=True, help_text='Designates whether this user should be treated as active.')
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField('staff status', default=False,
                                   help_text=_('Designates whether the user can log into this admin site.'))

    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = ActiveFamilyManager()
    all_objects = FamilyManager()
    instructors_objects = InstructorFamilyUserManager()
    managers_objects = ManagerFamilyUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('first_name', 'last_name', 'zipcode', 'city', 'country')

    class Meta:
        get_latest_by = "date_joined"
        ordering = ('last_name', 'first_name')
        verbose_name = _("User")
        verbose_name_plural = _("Users")

    def save(self, *args, **kwargs):
        from registrations.models import RegistrationsProfile
        from django.db import ProgrammingError
        super(FamilyUser, self).save(*args, **kwargs)
        if not hasattr(self, 'profile'):
            try:
                RegistrationsProfile.objects.get_or_create(user=self)
            except ProgrammingError:
                # we are running from shell where no tenant has been selected.
                pass

    def get_full_name(self):
        full_name = u'{} {}'.format(self.first_name, self.last_name)
        return full_name.strip().title()

    @property
    def best_phone(self):
        return self.private_phone2 or self.private_phone or self.private_phone3

    @property
    def full_name(self):
        return self.get_full_name()

    @property
    def updatable_children(self):
        from registrations.models import Child
        return self.children.filter(status=Child.STATUS.imported).count()

    @property
    def nb_notifications(self):
        return self.updatable_children

    def get_short_name(self):
        return self.first_name

    def get_initials(self):
        if self.first_name and self.last_name:
            initial = self.first_name[:1].upper()
            match = re.search(r'[A-Z]', self.last_name)
            if match:
                # Use first capital letter
                initial += match.group()
            else:
                # No capitals found; just use first letter
                initial += self.last_name[:1].upper()
        else:
            initial = self.email[:1].upper()
        return initial

    @property
    def children_names(self):
        return ', '.join([unicode(child) for child in self.children.all()])

    @property
    def has_open_bills(self):
        if hasattr(self, 'opened_bills'):
            return self.opened_bills > 0
        return self.bills.filter(status=Bill.STATUS.waiting).exists()

    @property
    def paid(self):
        if hasattr(self, 'opened_bills'):
            return self.opened_bills == 0
        return not self.has_open_bills

    @property
    def has_open_registrations(self):
        if hasattr(self, 'waiting_registrations'):
            return self.waiting_registrations > 0
        return self.get_registrations(validated=False).exists()

    @property
    def finished_registrations(self):
        if hasattr(self, 'waiting_registrations'):
            return self.waiting_registrations == 0
        return not self.has_open_registrations

    @property
    def has_registrations(self):
        return Registration.objects.validated().filter(child__family=self).exists()

    @property
    def last_registration(self):
        registrations = Registration.objects.validated().filter(child__family=self).order_by('-created')
        if not registrations.exists():
            return None
        return registrations.first().created

    def get_registrations(self, validated=True):
        if validated:
            queryset = Registration.objects.validated()
        else:
            queryset = Registration.objects.waiting()
        return queryset.filter(child__in=self.children.all())

    def get_absolute_url(self):
        return reverse('profiles_account')

    def get_manager(self):
        from backend import MANAGERS_GROUP
        if self.is_superuser or self.is_admin:
            return True
        return MANAGERS_GROUP in self.groups.values_list("name", flat=True)

    def set_manager(self, value):
        from backend import MANAGERS_GROUP
        managers = Group.objects.get(name=MANAGERS_GROUP)
        if value:
            managers.user_set.add(self)
        else:
            managers.user_set.remove(self)

    is_manager = property(get_manager, set_manager)

    def get_instructor_status(self):
        from backend import INSTRUCTORS_GROUP
        if self.is_superuser or self.is_admin:
            return True
        return INSTRUCTORS_GROUP in self.groups.values_list("name", flat=True)

    def set_instructor_status(self, value):
        from backend import INSTRUCTORS_GROUP
        instructors = Group.objects.get(name=INSTRUCTORS_GROUP)
        if value:
            instructors.user_set.add(self)
        else:
            instructors.user_set.remove(self)

    is_instructor = property(get_instructor_status, set_instructor_status)

    def is_instructor_of(self, course):
        return course in self.courses.all()

    def has_module_perms(self, app_label):
        staff_apps = ['activities', 'backend', 'extended_flatpages' 'profiles', 'registrations', 'schools']
        # no registration nore auth
        if self.is_superuser:
            return True
        if self.is_staff and app_label in staff_apps:
            return True
        return False

    def get_update_url(self):
        return reverse('backend:user-update', kwargs={'pk': self.pk})

    def get_delete_url(self):
        return reverse('backend:user-delete', kwargs={'pk': self.pk})

    def get_payment_url(self):
        return reverse('backend:user-pay', kwargs={'pk': self.pk})

    def get_backend_url(self):
        return reverse('backend:user-detail', kwargs={'pk': self.pk})

    def get_email_string(self):
        return "%s %s <%s>" % (self.first_name, self.last_name, self.email)

    def __unicode__(self):
        return self.get_email_string()


class VisibleYearManager(models.Manager):
    def get_queryset(self):
        return super(VisibleYearManager, self).get_queryset().filter(visible=True)


class SchoolYear(models.Model):
    year = models.PositiveIntegerField(_("School year"), choices=SCHOOL_YEARS, unique=True)
    visible = models.BooleanField(default=True)

    objects = models.Manager()
    visible_objects = VisibleYearManager()

    def __unicode__(self):
        try:
            return unicode(dict(SCHOOL_YEARS)[self.year])
        except KeyError:
            return unicode(self.year)

    class Meta:
        verbose_name = _("School year")
        verbose_name_plural = _("School years")
        ordering = ('year',)


class School(models.Model):
    name = models.CharField(_("Name"), max_length=50)
    code = models.CharField(_("Code name"), max_length=50, blank=True)
    selectable = models.BooleanField(default=True)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _("school")
        verbose_name_plural = _("schools")


class City(models.Model):
    COUNTRY = Choices(('CH', _("Switzerland")),
                      ('FL', _("Liechtenstein")),
                      ('D', _("Germany")),
                      ('F', _("France")),
                      ('I', _("Italy")),
                      ('A', _("Austria")))
    zipcode = models.CharField(_("NPA"), max_length=5)
    name = models.CharField(_('Name'), max_length=100)
    country = models.CharField(_('Country'), max_length=2, choices=COUNTRY, default=COUNTRY.CH)

    class Meta:
        verbose_name = _("City")
        verbose_name_plural = _("Cities")
        ordering = ('zipcode', 'name')

    def __unicode__(self):
        return u'{} {}'.format(self.zipcode, self.name)
