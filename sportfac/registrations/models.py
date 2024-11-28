import os
import re
from datetime import date, datetime, timedelta
from tempfile import mkdtemp

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.files import File
from django.db import IntegrityError, connection, models, transaction
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from dateutil.relativedelta import relativedelta
from dynamic_preferences.registries import global_preferences_registry
from model_utils import Choices
from model_utils.models import StatusModel
from phonenumber_field.modelfields import PhoneNumberField

from sportfac.models import TimeStampedModel


class RegistrationManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(status=Registration.STATUS.canceled)

    def all_with_deleted(self):
        return super().get_queryset().all()

    def waiting(self):
        return self.get_queryset().filter(status=Registration.STATUS.waiting)

    def validated(self):
        return self.get_queryset().filter(status__in=(Registration.STATUS.valid, Registration.STATUS.confirmed))


class Registration(TimeStampedModel, StatusModel):
    STATUS = Choices(
        ("waiting", _("Waiting parent's confirmation")),
        ("valid", _("Validated by parent")),
        ("canceled", _("Canceled")),  # Canceled in American English, Cancelled in British English
        ("confirmed", _("Confirmed by administrator")),
    )
    REASON = Choices(
        ("expired", _("Expired")),
        ("admin", _("Manager decision")),
        ("instructor", _("Instructor decision")),
        ("moved", _("Moved to another course")),
    )

    course = models.ForeignKey(
        "activities.Course",
        related_name="participants",
        verbose_name=_("Course"),
        on_delete=models.CASCADE,
    )
    child = models.ForeignKey("Child", related_name="registrations", on_delete=models.CASCADE)
    bill = models.ForeignKey("Bill", related_name="registrations", null=True, blank=True, on_delete=models.SET_NULL)
    paid = models.BooleanField(default=False, verbose_name=_("Has been paid"))
    price = models.PositiveIntegerField(verbose_name=_("Price"), null=True, blank=True)
    allocation_account = models.ForeignKey(
        "activities.AllocationAccount",
        null=True,
        blank=True,
        related_name="registrations",
        verbose_name=_("Allocation account"),
        on_delete=models.SET_NULL,
    )
    transport = models.ForeignKey(
        "Transport",
        related_name="participants",
        null=True,
        blank=True,
        verbose_name=_("Transport information"),
        on_delete=models.SET_NULL,
    )
    confirmation_sent_on = models.DateField(_("Confirmation mail sent on"), null=True, blank=True)
    cancelation_person = models.ForeignKey("profiles.FamilyUser", null=True, blank=True, on_delete=models.SET_NULL)
    cancelation_reason = models.CharField(
        _("Cancelation reason"), max_length=20, null=True, blank=True, choices=REASON, db_index=True
    )
    cancelation_date = models.DateTimeField(_("Cancelation date"), null=True, blank=True)

    objects = RegistrationManager()
    all_objects = models.Manager()

    class Meta:
        unique_together = ("course", "child", "status")
        verbose_name = _("Registration")
        verbose_name_plural = _("Registrations")
        ordering = ("child__last_name", "child__first_name", "course__start_date")

    @property
    def cancel_url(self):
        return reverse("registrations:cancel-registration", kwargs={"pk": self.pk})

    @property
    def delete_url(self):
        return self.get_delete_url()

    @property
    def details_url(self):
        return self.get_details_url()

    @property
    def extra_needs(self):
        return self.course.extra.all().exclude(id__in=self.extra_infos.values_list("key"))

    @property
    def has_modifier(self):
        return sum([extra.price_modifier for extra in self.extra_infos.all()]) != 0

    @property
    def is_local_pricing(self):
        if self.course.local_city_override.exists():
            local_zipcodes = self.course.local_city_override.values_list("zipcode", flat=True)
        else:
            local_zipcodes = settings.KEPCHUP_LOCAL_ZIPCODES
        return self.child.family.zipcode in local_zipcodes

    @property
    def is_canceled(self):
        return self.status == self.STATUS.canceled

    @property
    def is_confirmed(self):
        return self.status == self.STATUS.confirmed

    @property
    def is_validated(self):
        return self.status == self.STATUS.valid

    @property
    def payment_method(self):
        if not self.paid:
            return None
        if settings.KEPCHUP_PAYMENT_METHOD == "datatrans":
            if self.bill and self.bill.datatrans_successful_transaction:
                return self.bill.datatrans_successful_transaction.payment_method
            return "cash"
        if settings.KETCHUP_PAYMENT_METHOD == "postfinance":
            if self.bill and self.bill.postfinance_successful_transaction:
                return self.bill.postfinance_successful_transaction.payment_method
            return "cash"
        return settings.KEPCHUP_PAYMENT_METHOD

    @property
    def update_url(self):
        return self.get_update_url()

    def cancel(self, reason=None, user=None):
        if not reason:
            reason = self.REASON.admin
        self.status = self.STATUS.canceled
        self.cancelation_reason = reason
        self.cancelation_person = user
        self.cancelation_date = now()
        if settings.KEPCHUP_USE_ABSENCES:
            self.delete_future_absences()
        # TODO: Send email to admin

    def create_future_absences(self):
        # move between courses:
        from absences.models import Absence

        for future_session in self.course.sessions.filter(date__gte=now()):
            Absence.objects.get_or_create(
                child=self.child,
                session=future_session,
                defaults={"status": Absence.STATUS.present},
            )

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            super().delete(*args, **kwargs)
            self.course.update_registrations(None)
            if self.bill:
                self.bill.save()
            else:
                # noinspection PyUnresolvedReferences
                self.child.family.profile.save()

    def expire(self):
        self.status = self.STATUS.canceled
        self.cancelation_reason = self.REASON.expired
        self.cancelation_date = now()
        self.save()

    def delete_future_absences(self):
        # move between courses:
        from absences.models import Absence

        for future_session in self.course.sessions.filter(date__gte=now()):
            Absence.objects.filter(
                child=self.child,
                session=future_session,
            ).delete()

    def get_backend_url(self):
        return reverse("backend:registration-detail", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse("backend:registration-delete", kwargs={"pk": self.pk})

    def get_details_url(self):
        return reverse("backend:registration-detail", kwargs={"pk": self.pk})

    def get_price(self):
        subtotal, __ = self.get_price_category()
        if subtotal is None:
            subtotal = 0
        modifier = sum([extra.price_modifier for extra in self.extra_infos.all()])
        if modifier is None:
            modifier = 0
        if subtotal + modifier > 0:
            # we don't want to give money to users :)
            return subtotal + modifier
        return 0

    def get_subtotal(self):
        return self.get_price_category()[0]

    def get_price_category(self):
        if settings.KEPCHUP_USE_DIFFERENTIATED_PRICES:
            from activities.models import Course

            # what are the registrations to the same activities already made in same family?
            same_family_regs = Registration.objects.filter(
                child__family=self.child.family, course__activity=self.course.activity
            ).order_by("created")
            if same_family_regs.exists() and same_family_regs.first() != self:
                # This child has a sibling, registered to the same activity => special rate for the second child +
                if self.is_local_pricing:
                    # tarif indigène
                    return (
                        self.course.price_local_family,
                        Course._meta.get_field("price_local_family").verbose_name,
                    )
                return (
                    self.course.price_family,
                    Course._meta.get_field("price_family").verbose_name,
                )
            if self.is_local_pricing:
                # tarif indigène
                return (
                    self.course.price_local,
                    Course._meta.get_field("price_local").verbose_name,
                )
            return self.course.price, _("Price for external people")
        return self.course.price, ""

    def get_update_url(self):
        return reverse("backend:registration-update", kwargs={"pk": self.pk})

    def is_valid(self):
        return self.extra_needs.count() == 0

    def overlap(self, r2):
        """Test if another registration object overlaps with this one."""
        if self.course.is_camp or r2.course.is_camp:
            # overlap if other dates are between this.start_date and this.end_date
            latest_start = max(self.course.start_date, r2.course.start_date)
            earliest_end = min(self.course.end_date, r2.course.end_date)
            delta = (earliest_end - latest_start).days + 1
            return delta > 0
        if self.course.is_multi_course or r2.course.is_multi_course:
            # frankly, it's a mess. We simply do not make recommendations
            return False

        # no overlap if course are not the same day
        if self.course.day != r2.course.day:
            return False

        same_days = (
            min(
                self.course.end_date - r2.course.start_date,
                r2.course.end_date - self.course.start_date,
            ).days
            + 1
        )

        # no overlap if periods do not superpose
        if not same_days > 0:
            return False
        # two children can attend same course
        if self.course == r2.course and self.child != r2.child:
            return False

        latest_start = max(self.course.start_time, r2.course.start_time)
        earliest_end = min(self.course.end_time, r2.course.end_time)
        delta = datetime.combine(date.today(), earliest_end) - datetime.combine(date.today(), latest_start)

        if delta.days < 0:
            # they don't overlap
            if 24 * 3600 - delta.seconds <= 1800:
                # less than half an hour between courses
                return True
            return False
        # they overlap
        return True

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if settings.KEPCHUP_ENABLE_ALLOCATION_ACCOUNTS and self.allocation_account is None:
                self.allocation_account = self.course.activity.allocation_account
            if not settings.KEPCHUP_NO_PAYMENT and self.price is None:
                self.price = self.get_price()
            super().save(*args, **kwargs)
            if self.bill:
                self.bill.save()
            else:
                profile, created = RegistrationsProfile.objects.get_or_create(user=self.child.family)
                profile.save()
            if settings.KEPCHUP_USE_ABSENCES:
                self.create_future_absences()
            self.course.update_registrations(self)

    def set_confirmed(self, send_confirmation=False):
        self.status = self.STATUS.confirmed
        if send_confirmation:
            from .tasks import send_confirmation as send_confirmation_task

            try:
                tenant_pk = connection.tenant.pk
            except AttributeError:
                tenant_pk = None
            transaction.on_commit(
                lambda: send_confirmation_task.delay(
                    user_pk=str(self.child.family.pk),
                    tenant_pk=tenant_pk,
                    language=get_language(),
                )
            )

    def set_paid(self):
        self.paid = True
        self.save(update_fields=["paid"])

    def set_valid(self):
        self.status = self.STATUS.valid

    def set_waiting(self):
        self.status = self.STATUS.waiting

    def __str__(self):
        out = _("%(child)s ⇒ course %(number)s (%(activity)s)") % {
            "child": self.child.full_name,
            "number": self.course.number,
            "activity": self.course.activity.name,
        }
        if self.status == self.STATUS.canceled:
            return "CANCELED - " + out
        return out


class Transport(TimeStampedModel):
    name = models.CharField(_("Label"), max_length=60, db_index=True, blank=False)

    class Meta:
        verbose_name = _("Transport")
        verbose_name_plural = _("Transports")

    def __str__(self):
        return self.name

    @property
    def backend_url(self):
        return reverse("backend:transport-detail", kwargs={"pk": self.pk})

    @property
    def update_url(self):
        return reverse("backend:transport-update", kwargs={"pk": self.pk})

    @property
    def delete_url(self):
        return reverse("backend:transport-delete", kwargs={"pk": self.pk})


class BillManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(status=Bill.STATUS.canceled)

    def all_with_deleted(self):
        return super().get_queryset().all()

    def waiting(self):
        return self.get_queryset().filter(status__in=(Bill.STATUS.just_created, Registration.STATUS.waiting))

    def paid(self):
        return self.get_queryset().filter(status=Bill.STATUS.paid)


class Bill(TimeStampedModel, StatusModel):
    METHODS = Choices(
        ("iban", _("Wire transfer")),
        ("datatrans", _("Credit card (datatrans)")),
        ("postfinance", _("Credit card (postfinance)")),
        ("on-site", _("On-Site payment")),
        ("external", _("External invoice")),
    )
    STATUS = Choices(
        ("just_created", _("Just created")),
        ("waiting", _("Waiting parent's payment")),
        ("paid", _("Paid by parent")),
        ("canceled", _("Canceled by administrator")),
    )
    billing_identifier = models.CharField(_("Billing identifier"), max_length=45, blank=True)
    payment_method = models.CharField(_("Payment method"), choices=METHODS, max_length=20, blank=True)
    family = models.ForeignKey("profiles.FamilyUser", related_name="bills", null=True, on_delete=models.CASCADE)
    total = models.PositiveIntegerField(default=0, verbose_name=_("Total to be paid"))
    due_date = models.DateField(_("Due date"), null=True, blank=True)
    reminder_sent = models.BooleanField(_("Reminder sent"), default=False)
    reminder_sent_date = models.DateTimeField(_("Reminder sent date"), null=True, blank=True)
    pdf = models.FileField(_("PDF"), null=True, blank=True)

    payment_date = models.DateTimeField(_("Payment date"), null=True, blank=True)

    objects = BillManager()

    class Meta:
        verbose_name = _("Bill")
        verbose_name_plural = _("Bills")
        ordering = ("-created",)

    @property
    def backend_url(self):
        return self.get_backend_url()

    @property
    def datatrans_successful_transaction(self):
        from payments.models import DatatransTransaction

        return DatatransTransaction.successful.filter(invoice=self).last()

    @property
    def postfinance_successful_transaction(self):
        from payments.models import PostfinanceTransaction

        return PostfinanceTransaction.successful.filter(invoice=self).last()

    @property
    def is_ok(self):
        return self.status != self.STATUS.waiting

    @property
    def is_paid(self):
        return self.status == self.STATUS.paid

    @property
    def is_wire_transfer(self):
        return self.payment_method == self.METHODS.iban

    @property
    def pay_url(self):
        return self.get_pay_url()

    @property
    def registrations_valid_to(self):
        if not settings.KEPCHUP_REGISTRATION_EXPIRE_MINUTES:
            return None
        return self.modified + timedelta(minutes=settings.KEPCHUP_REGISTRATION_EXPIRE_MINUTES)

    @transaction.atomic
    def close(self):
        self.status = self.STATUS.paid
        for registration in self.registrations.filter(status=Registration.STATUS.valid):
            registration.paid = True
            registration.save()
        for rental in self.rentals.all():
            rental.paid = True
            rental.save()

    def generate_pdf(self):
        from mailer.pdfutils import InvoiceRenderer

        renderer = InvoiceRenderer({"bill": self})
        filename = f"facture-{self.pk}.pdf"
        tempdir = mkdtemp()
        filepath = os.path.join(tempdir, filename)
        renderer.render_to_pdf(filepath)
        with open(filepath, "rb") as pdf_file:
            self.pdf.save(filename, File(pdf_file), save=True)
        self.save()

    def get_absolute_url(self):
        return reverse("registrations:registrations_bill_detail", kwargs={"pk": self.pk})

    def get_backend_url(self):
        return reverse("backend:bill-detail", kwargs={"pk": self.pk})

    def get_due_date(self):
        global_preferences = global_preferences_registry.manager()
        delay = global_preferences["payment__DELAY_DAYS"]
        if not self.created:
            self.created = now()
        return self.created + relativedelta(days=delay)

    def get_pay_url(self):
        return reverse("backend:bill-update", kwargs={"pk": self.pk})

    def get_update_url(self):
        return reverse("backend:bill-update", kwargs={"pk": self.pk})

    @transaction.atomic
    def save(self, force_status=False, *args, **kwargs):
        self.update_total()
        if not self.due_date:
            self.due_date = self.get_due_date()
        if not self.payment_method:
            self.payment_method = settings.KEPCHUP_PAYMENT_METHOD
        if not force_status:
            self.update_status()
        if self.is_paid and not self.payment_date:
            self.payment_date = now()
        super().save(*args, **kwargs)
        if not self.billing_identifier:
            self.update_billing_identifier()
        if self.family:
            self.family.save()

    def send_confirmation(self):
        from .tasks import send_bill_confirmation as send_confirmation_task

        try:
            tenant_pk = connection.tenant.pk
        except AttributeError:
            tenant_pk = None
        transaction.on_commit(
            lambda: send_confirmation_task.delay(
                user_pk=str(self.family.pk),
                bill_pk=self.pk,
                tenant_pk=tenant_pk,
                language=get_language(),
            )
        )

    def send_reminder(self):
        # 1. build context
        global_preferences = global_preferences_registry.manager()
        current_site = Site.objects.get_current()
        context = {
            "user": self.family,
            "registrations": self.registrations.filter(paid=False),
            "signature": global_preferences["email__SIGNATURE"],
            "site_name": current_site.name,
            "site_url": settings.DEBUG and "http://" + current_site.domain or "https://" + current_site.domain,
        }
        # 2. build text
        subject = render_to_string("registrations/reminder_mail_subject.txt", context=context)
        body = render_to_string("registrations/reminder_mail.txt", context=context)
        # 3. send mail
        from mailer.tasks import send_mail

        send_mail.delay(
            subject=subject,
            message=body,
            from_email=global_preferences["email__FROM_MAIL"],
            recipients=[self.family.get_email_string()],
            reply_to=[global_preferences["email__REPLY_TO_MAIL"]],
        )
        self.reminder_sent = True
        self.reminder_sent_date = now()
        self.save()

    def send_to_accountant(self):
        if not self.total:
            # Accountants do not care about bills with no total :)
            return
        if not settings.KEPCHUP_SEND_BILL_TO_ACCOUNTANT:
            return
        tenant = connection.get_tenant()

        tenant_preferences = tenant.preferences
        end = tenant_preferences["phase__END_REGISTRATION"]
        if now() < end:
            return

        from .tasks import send_invoice_pdf

        transaction.on_commit(
            lambda: send_invoice_pdf.delay(
                bill_pk=self.pk,
                tenant_pk=tenant.pk,
            )
        )

    def set_paid(self):
        self.status = self.STATUS.paid
        self.payment_date = now()
        for registration in self.registrations.all():
            registration.set_paid()
        for rental in self.rentals.all():
            rental.paid = True
            rental.save(update_fields=("paid",))
        self.save()

    def set_waiting(self):
        self.status = self.STATUS.waiting
        self.save()

    def cancel(self):
        for registration in self.registrations.filter(paid=False, price__gt=0):
            registration.cancel(reason=Registration.REASON.expired)
            try:
                registration.save()
            except IntegrityError:
                registration.delete()
        if self.rentals:
            for rental in self.rentals.all():
                rental.delete()

        self.status = self.STATUS.canceled
        self.save(force_status=True)

    def update_billing_identifier(self):
        if self.pk:
            name_part = slugify(self.family.last_name).split("-")
            number_part = str(self.pk)
            identifier = name_part + [number_part]
            if len("-".join(identifier)) <= 20:
                self.billing_identifier = "-".join(identifier)
            else:
                identifier = f"{name_part[0]}-{number_part}"
                if len(identifier) <= 20:
                    self.billing_identifier = identifier
                else:
                    self.billing_identifier = name_part[0][: (20 - len(number_part) - 1)] + "-" + number_part
            super().save()

    def update_total(self):
        registrations_price = sum(
            [registration.price for registration in self.registrations.all() if registration.price]
        )
        extra_price = sum(
            sum(extra_infos.price_modifier for extra_infos in reg.extra_infos.all())
            for reg in self.registrations.all()
        )
        rental_price = sum([rental.amount for rental in self.rentals.all()])
        self.total = registrations_price + extra_price + rental_price

    def update_status(self):
        if (
            self.status == "waiting"
            and self.registrations.exists()
            and not self.registrations.exclude(status=Registration.STATUS.canceled).filter(paid=False).exists()
        ):
            self.status = self.STATUS.paid

    def __str__(self):
        return self.billing_identifier


class ExtraInfo(TimeStampedModel):
    registration = models.ForeignKey(
        "registrations.Registration",
        related_name="extra_infos",
        on_delete=models.CASCADE,
        verbose_name=_("Registration"),
    )
    key = models.ForeignKey("activities.ExtraNeed", on_delete=models.CASCADE)
    value = models.CharField(max_length=255, blank=True)
    image = models.FileField(upload_to="extra_infos", blank=True, null=True)

    class Meta:
        ordering = ("key", "registration")

    @property
    def is_true(self):
        return self.value in ["True", "true", "1", "OUI", "oui", "Oui", 1, True]

    @property
    def is_false(self):
        return self.value in ["False", "false", "0", "NON", "non", "Non", 0, False]

    @property
    def require_image(self):
        return self.key.is_image and self.is_true

    @property
    def price_modifier(self):
        return self.key.price_dict.get(self.value, 0)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.registration.save()

    def __str__(self):
        return f"{self.key}: {self.value}"


class Child(TimeStampedModel, StatusModel):
    STATUS = Choices(
        ("updated", _("Updated")),
        ("imported", _("Imported")),
    )
    SEX = Choices(
        ("M", _("Male")),
        ("F", _("Female")),
    )
    NATIONALITY = Choices(
        ("CH", _("Swiss")),
        ("FL", _("Liechtenstein")),
        ("DIV", _("Other")),
    )
    LANGUAGE = Choices(
        ("D", "Deutsch"),
        ("E", "English"),
        ("F", "Français"),
        ("I", "Italiano"),
    )
    first_name = models.CharField(_("First name"), max_length=50)
    last_name = models.CharField(_("Last name"), max_length=50)
    sex = models.CharField(_("Sex"), max_length=1, choices=SEX)
    birth_date = models.DateField(_("Birth date"))
    nationality = models.CharField(choices=NATIONALITY, max_length=3, default=NATIONALITY.CH)
    language = models.CharField(choices=LANGUAGE, max_length=2, default=LANGUAGE.F)

    school_year = models.ForeignKey("profiles.SchoolYear", null=True, blank=True, on_delete=models.SET_NULL)
    building = models.ForeignKey(
        "schools.Building",
        related_name="students",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    teacher = models.ForeignKey(
        "schools.Teacher",
        related_name="students",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    family = models.ForeignKey(
        "profiles.FamilyUser",
        related_name="children",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    courses = models.ManyToManyField("activities.Course", through="registrations.Registration")

    id_lagapeo = models.IntegerField(
        db_index=True,
        unique=True,
        null=True,
        blank=True,
        verbose_name=_("Lagapeo Identification number"),
    )
    avs = models.CharField(max_length=16, blank=True, default="", verbose_name=_("AVS"))
    emergency_number = PhoneNumberField(_("Emergency number"), max_length=30, blank=True)
    school = models.ForeignKey(
        "profiles.School",
        related_name="students",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    other_school = models.CharField(_("Other school"), blank=True, max_length=50)
    bib_number = models.CharField(_("Bib number"), blank=True, max_length=20)
    is_blacklisted = models.BooleanField(_("Is blacklisted"), default=False, db_index=True)

    class Meta:
        ordering = (
            "last_name",
            "first_name",
        )
        abstract = False
        verbose_name = _("Child")
        verbose_name_plural = _("Children")

    @property
    def backend_url(self):
        return self.get_backend_url()

    @property
    def delete_url(self):
        return self.get_delete_url()

    @property
    def full_name(self):
        return self.get_full_name()

    @property
    def has_registrations(self):
        return self.registrations.exclude(status=Registration.STATUS.canceled).exists()

    @property
    def js_avs(self):
        avs = re.sub(r"\D", "", self.avs)
        if len(avs) != "13":
            return avs
        return f"{avs[:3]}.{avs[3:7]}.{avs[7:11]}.{avs[11:]}"

    @property
    def js_birth_date(self):
        return self.birth_date.strftime("%d.%m.%Y")

    @property
    def js_sex(self):
        if self.sex == self.SEX.M:
            return "h"
        return "f"

    @property
    def js_language(self):
        return {"D": "DE", "F": "FR", "I": "IT"}.get(self.language, "autre")

    @property
    def js_nationality(self):
        return {"CH": "CH", "FL": "LI"}.get(self.nationality, "autre")

    @property
    def js_country(self):
        if not self.family:
            return "CH"
        return {"CH": "CH", "FL": "LI", "F": "FR", "I": "IT", "A": "AT"}.get(self.family.country, "CH")

    @property
    def js_street(self):
        if not self.family:
            return ""
        return self.family.street_and_number[0]

    @property
    def js_street_number(self):
        if not self.family:
            return ""
        return self.family.street_and_number[1]

    @property
    def js_zipcode(self):
        if not self.family:
            return ""
        return self.family.zipcode

    @property
    def js_city(self):
        if not self.family:
            return ""
        return self.family.city

    @property
    def montreux_needs_appointment(self):
        from activities.models import ExtraNeed

        material_needs = ExtraNeed.objects.filter(question_label__icontains="matériel")
        return self.registrations.filter(
            extra_infos__key__in=material_needs, extra_infos__value__in=["OUI", 1, "1"]
        ).exists()

    @property
    def ordering_name(self):
        return f"{self.last_name.lower().strip()} {self.first_name.lower().strip()}"

    @property
    def school_name(self):
        if self.school:
            return self.school.name
        return self.other_school

    @property
    def update_url(self):
        return self.get_update_url()

    def get_announced_level(self, course):
        return ExtraInfo.objects.filter(
            registration__child=self,
            key__question_label__startswith="Niveau",
            registration__course__activity=course.activity,
        ).first()

    def get_backend_absences_url(self):
        return reverse("backend:child-absences", kwargs={"child": self.pk})

    def get_backend_detail_url(self):
        return reverse("backend:child-detail", kwargs={"child": self.pk})

    def get_backend_url(self):
        if self.family:
            return reverse("backend:user-detail", kwargs={"pk": self.family.pk})
        return self.get_update_url()

    def get_delete_url(self):
        return reverse("backend:child-delete", kwargs={"child": self.pk})

    def get_full_name(self):
        full_name = f"{self.first_name.title()} {self.last_name.title()}"
        return full_name.strip()

    def get_update_url(self):
        return reverse("backend:child-update", kwargs={"child": self.pk})

    def save(self, *args, **kwargs):
        if settings.KEPCHUP_EMERGENCY_NUMBER_ON_PARENT and self.family:
            self.emergency_number = self.family.best_phone
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name()


class ChildActivityLevel(TimeStampedModel):
    LEVELS = Choices(
        ("NP", "NP"),
        ("CM", "CM"),
        ("ABS", "ABS"),
        ("NPA", "NPA"),
        ("NPB", "NPB"),
        ("NPC", "NPC"),
        ("A 1A", "A 1A"),
        ("A 1B", "A 1B"),
        ("A 1C", "1C"),
        ("A 2A", "2A"),
        ("A 2B", "A 2B"),
        ("A 2C", "A 2C"),
        ("A 3A", "A 3A"),
        ("A 3B", "A 3B"),
        ("A 3C", "A 3C"),
        ("A 4A", "A 4A"),
        ("A 4B", "A 4B"),
        ("A 4C", "A 4C"),
        ("A 5A", "A 5A"),
        ("A 5B", "A 5B"),
        ("A 5C", "A 5C"),
        ("A 6A", "A 6A"),
        ("A 6B", "A 6B"),
        ("A 6C", "A 6C"),
        ("A 7A", "A 7A"),
        ("A 7B", "A 7B"),
        ("A 7C", "A 7C"),
        ("S 1A", "S 1A"),
        ("S 1B", "S 1B"),
        ("S 1C", "S 1C"),
        ("S 2A", "S 2A"),
        ("S 2B", "S 2B"),
        ("S 2C", "S 2C"),
        ("S 3A", "S 3A"),
        ("S 3B", "S 3B"),
        ("S 3C", "S 3C"),
        ("S 4A", "S 4A"),
        ("S 4B", "S 4B"),
        ("S 4C", "S 4C"),
        ("S 5A", "S 5A"),
        ("S 5B", "S 5B"),
        ("S 5C", "S 5C"),
        ("S 6A", "S 6A"),
        ("S 6B", "S 6B"),
        ("S 6C", "S 6C"),
        ("S 7A", "S 7A"),
        ("S 7B", "S 7B"),
        ("S 7C", "S 7C"),
    )

    before_level = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_("Level -1"),
    )
    after_level = models.CharField(choices=LEVELS, max_length=5, blank=True, verbose_name=_("End course level"))
    note = models.CharField(max_length=50, verbose_name=_("Note"), blank=True)
    activity = models.ForeignKey(
        "activities.Activity",
        related_name="levels",
        verbose_name=_("Course"),
        on_delete=models.CASCADE,
    )
    child = models.ForeignKey("Child", related_name="levels", on_delete=models.CASCADE)

    class Meta:
        unique_together = ("activity", "child")

    @property
    def api_url(self):
        return self.get_api_url()

    def get_api_url(self):
        return reverse("api:level-detail", kwargs={"pk": self.pk})


class RegistrationValidation(TimeStampedModel):
    user = models.ForeignKey("profiles.FamilyUser", related_name="validations", null=True, on_delete=models.SET_NULL)
    invoice = models.OneToOneField(
        "registrations.Bill", related_name="validation", null=True, blank=True, on_delete=models.CASCADE
    )
    consent_given = models.BooleanField(_("Consent given"), default=False)

    def __str__(self):
        return f"Validation for {self.user}"


class RegistrationsProfile(TimeStampedModel):
    """
    This model acts as a cache to avoid useless comparisons
    """

    user = models.OneToOneField("profiles.FamilyUser", related_name="profile", null=True, on_delete=models.SET_NULL)

    has_paid_all = models.BooleanField(default=False, blank=True)
    finished_registering = models.BooleanField(default=False, blank=True, editable=False)
    last_registration = models.DateTimeField(null=True, blank=True, editable=False)

    def save(self, *args, **kwargs):
        self.has_paid_all = self.user.paid
        self.finished_registering = self.user.finished_registrations
        self.last_registration = self.user.last_registration
        super().save(*args, **kwargs)
