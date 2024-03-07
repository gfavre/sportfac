import os
import re
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models, transaction
from django.db.models.aggregates import Count
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from activities.models import SCHOOL_YEARS
from django_countries.fields import CountryField
from localflavor.generic.countries.sepa import IBAN_SEPA_COUNTRIES
from localflavor.generic.models import IBANField
from model_utils import Choices
from model_utils.fields import AutoCreatedField, AutoLastModifiedField
from phonenumber_field.modelfields import PhoneNumberField
from registrations.models import Bill, Registration

from .ahv import AHVField
from .utils import get_street_and_number


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
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, last_name, zipcode, city, password, **extra_fields):
        """
        Creates and saves a superuser with the given email, favorite topping and password.
        """
        user = self.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            zipcode=zipcode,
            city=city,
            password=password,
            **extra_fields,
        )
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class ActiveFamilyManager(FamilyManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class InstructorFamilyUserManager(ActiveFamilyManager):
    def get_queryset(self):
        return super().get_queryset().annotate(num_courses=Count("course")).filter(num_courses__gt=0)


class ManagerFamilyUserManager(ActiveFamilyManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_manager=True)


SETTINGS_NAME = os.environ.get("DJANGO_SETTINGS_MODULE", "").split(".")[-1]


class FamilyUser(PermissionsMixin, AbstractBaseUser):
    COUNTRY = Choices(
        ("CH", _("Switzerland")),
        ("FL", _("Liechtenstein")),
        ("D", _("Germany")),
        ("F", _("France")),
        ("I", _("Italy")),
        ("A", _("Austria")),
    )
    GENDERS = Choices(("f", _("Female")), ("m", _("Male")))
    PERMIT_TYPES = Choices(
        ("L", _("L - Short-term residence permit")),
        ("B", _("B - Residence permit")),
        ("C", _("C - Settlement permit")),
        ("Ci", _("Ci - Residence permit with gainful employment")),
        ("G", _("G - Cross-border commuter permit")),
        ("F", _("F - Provisionally admitted foreigners")),
        ("N", _("N - Permit for asylum-seekers")),
        ("S", _("S - People in need of protection")),
    )

    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    external_identifier = models.CharField(verbose_name=_("Identifier"), max_length=255, blank=True, null=True)
    email = models.EmailField(verbose_name=_("Email address"), max_length=255, unique=True, db_index=True)
    first_name = models.CharField(_("First name"), max_length=30, blank=True)
    last_name = models.CharField(_("Last name"), max_length=30, blank=True)
    address = models.TextField(_("Street"), blank=True)
    zipcode = models.CharField(_("NPA"), blank=True, max_length=5)
    city = models.CharField(_("City"), max_length=100, blank=True)
    country = models.CharField(_("Country"), max_length=2, choices=COUNTRY, default=COUNTRY.CH, blank=True)
    private_phone = PhoneNumberField(_("Home phone"), max_length=30, blank=True)
    private_phone2 = PhoneNumberField(_("Mobile phone"), max_length=30, blank=True)
    private_phone3 = PhoneNumberField(_("Other phone"), max_length=30, blank=True)

    # TODO: move me to a separate SupervisorInfo model...
    iban = IBANField(include_countries=IBAN_SEPA_COUNTRIES, blank=True)
    birth_date = models.DateField(_("Birth date"), null=True, blank=True)
    ahv = AHVField(_("AHV number"), help_text=_("New AHV number, e.g. 756.1234.5678.90"), blank=True)
    js_identifier = models.CharField(_("J+S identifier"), max_length=30, blank=True)
    is_mep = models.BooleanField(default=False, verbose_name=_("Is sports teacher"))
    is_teacher = models.BooleanField(default=False, verbose_name=_("Is teacher"))
    gender = models.CharField(_("Gender"), choices=GENDERS, blank=True, max_length=1)
    nationality = CountryField(_("Nationality"), blank=True)
    permit_type = models.CharField(_("Permit type"), max_length=2, choices=PERMIT_TYPES, blank=True, null=True)
    bank_name = models.CharField(_("Bank name"), max_length=50, blank=True)

    is_active = models.BooleanField(
        default=True, help_text="Designates whether this user should be treated as active."
    )
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(
        "staff status",
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_restricted_manager = models.BooleanField(_("Is restricted manager"), default=False)
    is_manager = models.BooleanField(_("Is manager"), default=False)
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

    created = AutoCreatedField(_("created"))
    modified = AutoLastModifiedField(_("modified"))
    created_on = models.CharField(
        _("Instance name"), max_length=255, blank=True, default=SETTINGS_NAME, editable=False
    )

    objects = FamilyManager()
    active_objects = ActiveFamilyManager()
    instructors_objects = InstructorFamilyUserManager()
    managers_objects = ManagerFamilyUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ("first_name", "last_name", "zipcode", "city", "country")

    class Meta:
        get_latest_by = "date_joined"
        ordering = ("last_name", "first_name")
        verbose_name = _("User")
        verbose_name_plural = _("Users")

    @property
    def best_phone(self):
        return self.private_phone2 or self.private_phone or self.private_phone3

    @property
    def children_names(self):
        return ", ".join([str(child) for child in self.children.all()])

    @property
    def children_who_can_take_appointments(self):
        if settings.KEPCHUP_APPOINTMENTS_WITHOUT_WIZARD:
            return self.children.all()
        return [child for child in self.children.all() if child.montreux_needs_appointment]

    @property
    def course_names(self):
        return ", ".join([str(ci.course.short_name) for ci in self.coursesinstructors_set.all()])

    @property
    def country_iso_3166(self):
        return {
            "CH": "CH",
            "FL": "LI",
            "D": "DE",
            "F": "FR",
            "I": "IT",
            "A": "AT",
        }[self.country]

    @property
    def full_name(self):
        return self.get_full_name()

    @property
    def finished_registrations(self):
        if hasattr(self, "waiting_registrations"):
            return self.waiting_registrations == 0
        return not self.has_open_registrations

    @property
    def has_open_bills(self):
        if hasattr(self, "opened_bills"):
            return self.opened_bills > 0
        return self.bills.filter(status=Bill.STATUS.waiting).exists()

    @property
    def has_open_registrations(self):
        if hasattr(self, "waiting_registrations"):
            return self.waiting_registrations > 0
        return self.get_registrations(validated=False).exists()

    @property
    def has_registrations(self):
        return Registration.objects.validated().filter(child__family=self).exists()

    @property
    def is_kepchup_staff(self):
        return self.is_manager or self.is_restricted_manager or self.is_superuser or self.is_instructor

    @property
    def is_instructor(self):
        return self.coursesinstructors_set.exists()

    @property
    def last_registration(self):
        registrations = Registration.objects.validated().filter(child__family=self).order_by("-created")
        if not registrations.exists():
            return None
        return registrations.first().created

    @property
    def montreux_needs_appointment(self):
        from activities.models import ExtraNeed

        material_needs = ExtraNeed.objects.filter(question_label__icontains="matériel")
        registrations = Registration.objects.filter(child__family=self)
        return registrations.filter(
            extra_infos__key__in=material_needs, extra_infos__value__in=["OUI", 1, "1"]
        ).exists()

    @property
    def montreux_missing_appointments(self):
        from activities.models import ExtraNeed
        from appointments.models import Appointment, AppointmentType

        material_needs = ExtraNeed.objects.filter(question_label__icontains="matériel")
        registrations = Registration.objects.filter(child__family=self).prefetch_related("extra_infos")
        appointment_periods = AppointmentType.objects.all()
        missing_appointments = []
        for registration in registrations.filter(
            extra_infos__key__in=material_needs, extra_infos__value__in=["OUI", 1, "1"]
        ).select_related("child"):
            types = [app.appointment_type for app in Appointment.objects.filter(child=registration.child)]
            if set(types) != set(appointment_periods):
                missing_appointments.append((registration.child, set(appointment_periods) - set(types)))
        return missing_appointments

    @property
    def nb_notifications(self):
        return self.updatable_children

    @property
    def paid(self):
        if hasattr(self, "opened_bills"):
            return self.opened_bills == 0
        return not self.has_open_bills

    @property
    def street_and_number(self):
        return get_street_and_number(self.address)

    @property
    def updatable_children(self):
        from registrations.models import Child

        return self.children.filter(status=Child.STATUS.imported).count()

    def get_absolute_url(self):
        return reverse("profiles:profiles_account")

    def get_backend_url(self):
        return reverse("backend:user-detail", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse("backend:user-delete", kwargs={"pk": self.pk})

    def get_email_string(self):
        return f"{self.first_name} {self.last_name} <{self.email}>"

    def get_full_name(self):
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip().title()

    def get_initials(self):
        if self.first_name and self.last_name:
            initial = self.first_name[:1].upper()
            match = re.search(r"[A-Z]", self.last_name)
            if match:
                # Use first capital letter
                initial += match.group()
            else:
                # No capitals found; just use first letter
                initial += self.last_name[:1].upper()
            return initial
        return self.email[:1].upper()

    def get_payment_url(self):
        return reverse("backend:user-pay", kwargs={"pk": self.pk})

    def get_registrations(self, validated=True):
        if validated:
            queryset = Registration.objects.validated()
        else:
            queryset = Registration.objects.waiting()
        return queryset.filter(child__in=self.children.all())

    def get_short_name(self):
        return self.first_name

    def get_update_url(self):
        return reverse("backend:user-update", kwargs={"pk": self.pk})

    def has_module_perms(self, app_label):
        staff_apps = [
            "activities",
            "backend",
            "extended_flatpages",
            "profiles",
            "registrations",
            "schools",
        ]
        # no registration nore auth
        if self.is_superuser:
            return True
        if self.is_staff and app_label in staff_apps:
            return True
        return False

    def is_instructor_of(self, course):
        return course in self.course.all()

    def save(self, create_profile=True, sync=True, *args, **kwargs):
        from django.db import ProgrammingError

        from registrations.models import RegistrationsProfile

        super().save(*args, **kwargs)
        if create_profile:
            try:
                profile, created = RegistrationsProfile.objects.get_or_create(user=self)
                if not created:
                    profile.save()
            except ProgrammingError:
                # we are running from shell where no tenant has been selected.
                pass
        if len(settings.DATABASES) > 1 and sync:
            from .tasks import LOCAL_DB, save_to_master

            transaction.on_commit(lambda: save_to_master(self.pk, kwargs.get("using", LOCAL_DB)))

    def soft_delete(self):
        from activities.models import CoursesInstructors

        self.is_active = False
        self.email = f"deleted_{self.pk}_{self.email}"
        self.is_manager = False
        CoursesInstructors.objects.filter(instructor=self).delete()
        for child in self.children.all():
            child.delete()
        self.save()

    def __str__(self):
        return self.get_email_string()


class VisibleYearManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(visible=True)


class SchoolYear(models.Model):
    year = models.PositiveIntegerField(_("School year"), choices=SCHOOL_YEARS, unique=True)
    visible = models.BooleanField(default=True)

    objects = models.Manager()
    visible_objects = VisibleYearManager()

    def __str__(self):
        return settings.KEPCHUP_YEAR_NAMES.get(self.year, str(self.year))

    class Meta:
        verbose_name = _("School year")
        verbose_name_plural = _("School years")
        ordering = ("year",)


class School(models.Model):
    name = models.CharField(_("Name"), max_length=50)
    code = models.CharField(_("Code name"), max_length=50, blank=True)
    selectable = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("school")
        verbose_name_plural = _("schools")
        ordering = ("name",)


class City(models.Model):
    COUNTRY = Choices(
        ("CH", _("Switzerland")),
        ("FL", _("Liechtenstein")),
        ("D", _("Germany")),
        ("F", _("France")),
        ("I", _("Italy")),
        ("A", _("Austria")),
    )
    zipcode = models.CharField(_("NPA"), max_length=5)
    name = models.CharField(_("Name"), max_length=100)
    country = models.CharField(_("Country"), max_length=2, choices=COUNTRY, default=COUNTRY.CH)

    class Meta:
        verbose_name = _("City")
        verbose_name_plural = _("Cities")
        ordering = ("zipcode", "name")

    def __str__(self):
        return f"{self.zipcode} {self.name}"
