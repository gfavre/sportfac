# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date, datetime

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import connection, models, transaction
from django.template.defaultfilters import slugify
from django.utils.timezone import now
from django.utils.translation import get_language, ugettext_lazy as _

from model_utils import Choices
from model_utils.models import StatusModel
from phonenumber_field.modelfields import PhoneNumberField

from sportfac.models import TimeStampedModel


class RegistrationManager(models.Manager):
    def get_queryset(self):
        return super(RegistrationManager, self).get_queryset().exclude(status=Registration.STATUS.canceled)

    def all_with_deleted(self):
        return super(RegistrationManager, self).get_queryset().all()

    def waiting(self):
        return self.get_queryset().filter(status=Registration.STATUS.waiting)

    def validated(self):
        return self.get_queryset().filter(status__in=(Registration.STATUS.valid, Registration.STATUS.confirmed))


class Registration(TimeStampedModel, StatusModel):
    STATUS = Choices(
        ('waiting', _("Waiting parent's confirmation")),
        ('valid', _("Validated by parent")),
        ('canceled', _("Canceled by administrator")),
        ('confirmed', _("Confirmed by administrator")),
    )

    course = models.ForeignKey('activities.Course', related_name="participants", verbose_name=_("Course"),
                               on_delete=models.CASCADE)
    child = models.ForeignKey('Child', related_name="registrations",
                              on_delete=models.CASCADE)
    bill = models.ForeignKey('Bill', related_name="registrations", null=True, blank=True,
                             on_delete=models.SET_NULL)
    paid = models.BooleanField(default=False, verbose_name=_("Has paid"))
    price = models.PositiveIntegerField(null=True, blank=True)
    allocation_account = models.ForeignKey('activities.AllocationAccount', null=True, blank=True, related_name='registrations',
                                           verbose_name=_("Allocation account"))
    transport = models.ForeignKey('Transport', related_name='participants', null=True, blank=True,
                                  verbose_name=_("Transport information"),
                                  on_delete=models.SET_NULL)
    confirmation_sent_on = models.DateField(_("Confirmation mail sent on"), null=True, blank=True)

    objects = RegistrationManager()

    class Meta:
        unique_together = ('course', 'child', 'status')
        verbose_name = _("Registration")
        verbose_name_plural = _("Registrations")
        ordering = ('child__last_name', 'child__first_name', 'course__start_date')

    @property
    def cancel_url(self):
        return reverse('cancel-registration', kwargs={'pk': self.pk})

    @property
    def delete_url(self):
        return self.get_delete_url()

    @property
    def extra_needs(self):
        return self.course.extra.all().exclude(id__in=self.extra_infos.values_list('key'))

    @property
    def has_modifier(self):
        return sum([extra.price_modifier for extra in self.extra_infos.all()]) != 0

    @property
    def update_url(self):
        return self.get_update_url()

    def cancel(self):
        self.status = self.STATUS.canceled
        if settings.KEPCHUP_USE_ABSENCES:
            self.delete_future_absences()

    def create_future_absences(self):
        # move between courses:
        from absences.models import Absence
        for future_session in self.course.sessions.filter(date__gte=now()):
            Absence.objects.get_or_create(
                child=self.child, session=future_session,
                defaults={'status': Absence.STATUS.present}
            )

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            super(Registration, self).delete(*args, **kwargs)
            self.course.save()
            if self.bill:
                self.bill.save()
            else:
                self.child.family.profile.save()

    def delete_future_absences(self):
        # move between courses:
        from absences.models import Absence
        for future_session in self.course.sessions.filter(date__gte=now()):
            Absence.objects.filter(
                child=self.child, session=future_session,
            ).delete()

    def get_delete_url(self):
        return reverse('backend:registration-delete', kwargs={'pk': self.pk})

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

    def get_price_category(self):
        if settings.KEPCHUP_USE_DIFFERENTIATED_PRICES:
            from activities.models import Course
            same_family_regs = Registration.objects.filter(child__family=self.child.family,
                                                           course__activity=self.course.activity).order_by('created')
            if same_family_regs.count() > 1 and same_family_regs.first != self:
                # This child has a sibling, registered to the same activity => special rate
                if self.child.family.zipcode in settings.KEPCHUP_LOCAL_ZIPCODES:
                    # tarif indigène
                    return self.course.price_local_family, Course._meta.get_field('price_local_family').verbose_name
                else:
                    return self.course.price_family, Course._meta.get_field('price_family').verbose_name
            else:
                if self.child.family.zipcode in settings.KEPCHUP_LOCAL_ZIPCODES:
                    # tarif indigène
                    return self.course.price_local, Course._meta.get_field('price_local').verbose_name
                else:
                    return self.course.price, _("Price for external people")
        return self.course.price, ''

    def get_update_url(self):
        return reverse('backend:registration-update', kwargs={'pk': self.pk})

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

        same_days = min(self.course.end_date - r2.course.start_date,
                        r2.course.end_date - self.course.start_date).days + 1

        # no overlap if periods do not superpose
        if not same_days > 0:
            return False
        # two children can attend same course
        if self.course == r2.course and self.child != r2.child:
            return False

        latest_start = max(self.course.start_time, r2.course.start_time)
        earliest_end = min(self.course.end_time, r2.course.end_time)
        delta = (datetime.combine(date.today(), earliest_end) - datetime.combine(date.today(), latest_start))

        if delta.days < 0:
            # they don't overlap
            if 24 * 3600 - delta.seconds <= 1800:
                # less than half an hour between courses
                return True
            return False
        else:
            # they overlap
            return True

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if settings.KEPCHUP_ENABLE_ALLOCATION_ACCOUNTS and self.allocation_account is None:
                self.allocation_account = self.course.activity.allocation_account
            if not settings.KEPCHUP_NO_PAYMENT and self.price is None:
                self.price = self.get_price()
            with transaction.atomic():
                super(Registration, self).save(*args, **kwargs)
                if self.bill:
                    self.bill.save()
                else:
                    self.child.family.profile.save()
                self.course.save()

    def set_confirmed(self, send_confirmation=False):
        self.status = self.STATUS.confirmed
        if send_confirmation:
            from .tasks import send_confirmation as send_confirmation_task
            try:
                tenant_pk = connection.tenant.pk
            except AttributeError:
                tenant_pk = None
            transaction.on_commit(lambda: send_confirmation_task.delay(
                user_pk=str(self.child.family.pk),
                tenant_pk=tenant_pk,
                language=get_language(),
            ))
        if settings.KEPCHUP_USE_ABSENCES:
            self.create_future_absences()

    def set_valid(self):
        self.status = self.STATUS.valid
        if settings.KEPCHUP_USE_ABSENCES:
            self.create_future_absences()

    def set_waiting(self):
        self.status = self.STATUS.waiting

    def __unicode__(self):
        out = _(u'%(child)s ⇒ course %(number)s (%(activity)s)') % {
            'child': self.child.full_name,
            'number': self.course.number,
            'activity': self.course.activity.name
        }
        if self.status == self.STATUS.canceled:
            out = 'CANCELED - ' + out
        return out


class Transport(TimeStampedModel):
    name = models.CharField(_('Label'), max_length=60, db_index=True, blank=False)

    class Meta:
        verbose_name = _("Transport")
        verbose_name_plural = _("Transports")

    def __unicode__(self):
        return self.name

    @property
    def backend_url(self):
        return reverse('backend:transport-detail', kwargs={'pk': self.pk})

    @property
    def update_url(self):
        return reverse('backend:transport-update', kwargs={'pk': self.pk})

    @property
    def delete_url(self):
        return reverse('backend:transport-delete', kwargs={'pk': self.pk})


class BillManager(models.Manager):
    def get_queryset(self):
        return super(BillManager, self).get_queryset().exclude(status=Bill.STATUS.canceled)

    def all_with_deleted(self):
        return super(BillManager, self).get_queryset().all()

    def waiting(self):
        return self.get_queryset().filter(status__in=(Bill.STATUS.just_created, Registration.STATUS.waiting))

    def paid(self):
        return self.get_queryset().filter(status=Bill.STATUS.paid)


class Bill(TimeStampedModel, StatusModel):
    METHODS = Choices(
        ('iban', _("Later with wire transfer")),
        ('datatrans', _("immediate with credit card (datatrans)")),
    )
    STATUS = Choices(
        ('just_created', _("Just created")),
        ('waiting', _("Waiting parent's payment")),
        ('paid', _("Paid by parent")),
        ('canceled', _("Canceled by administrator")),
    )
    billing_identifier = models.CharField(_('Billing identifier'), max_length=45, blank=True)
    payment_method = models.CharField(
        _("Payment method"), choices=METHODS,
        max_length=20, blank=True)
    family = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='bills',
                               null=True, on_delete=models.CASCADE)
    total = models.PositiveIntegerField(default=0, verbose_name=_("Total to be paid"))
    reminder_sent = models.BooleanField(_("Reminder sent"), default=False)
    reminder_sent_date = models.DateTimeField(_("Reminder sent date"), null=True, blank=True)

    objects = BillManager()

    class Meta:
        verbose_name = _("Bill")
        verbose_name_plural = _("Bills")
        ordering = ('-created', )

    @property
    def backend_url(self):
        return self.get_backend_url()

    @property
    def datatrans_successful_transaction(self):
        from payments.models import DatatransTransaction
        try:
            return self.datatrans_transactions.filter(status=DatatransTransaction.STATUS.authorized).last()
        except DatatransTransaction.DoesNotExist:
            return None

    @property
    def is_ok(self):
        return self.status != self.STATUS.waiting

    @property
    def is_paid(self):
        return self.status in (self.STATUS.paid, self.STATUS.canceled)

    @property
    def is_wire_transfer(self):
        return self.payment_method == self.METHODS.iban

    @property
    def pay_url(self):
        return self.get_pay_url()

    @transaction.atomic
    def close(self):
        self.status = self.STATUS.paid
        for registration in self.registrations.filter(status=Registration.STATUS.valid):
            registration.paid = True
            registration.save()

    def get_absolute_url(self):
        return reverse('registrations_bill_detail', kwargs={'pk': self.pk})

    def get_backend_url(self):
        return reverse('backend:bill-detail', kwargs={'pk': self.pk})

    def get_pay_url(self):
        return reverse('backend:bill-update', kwargs={'pk': self.pk})

    @transaction.atomic
    def save(self, force_status=False, *args, **kwargs):
        if not self.payment_method:
            if settings.KEPCHUP_PAYMENT_METHOD == 'wire_transfer':
                self.payment_method = self.METHODS.IBAN
            elif settings.KEPCHUP_PAYMENT_METHOD == 'datatrans':
                self.payment_method = self.METHODS.datatrans
        self.update_total()
        if not force_status:
            self.update_status()
        if not self.billing_identifier:
            self.update_billing_identifier()
        super(Bill, self).save(*args, **kwargs)
        if self.family:
            self.family.save()

    def send_confirmation(self):
        from .tasks import send_bill_confirmation as send_confirmation_task
        try:
            tenant_pk = connection.tenant.pk
        except AttributeError:
            tenant_pk = None
        transaction.on_commit(lambda: send_confirmation_task.delay(
            user_pk=str(self.family.pk),
            bill_pk=self.pk,
            tenant_pk=tenant_pk,
            language=get_language(),
        ))

    def set_paid(self):
        self.status = self.STATUS.paid
        self.save()

    def set_waiting(self):
        self.status = self.STATUS.waiting
        self.save()

    def update_billing_identifier(self):
        if self.pk:
            self.billing_identifier = slugify('%s-%i' % (self.family.last_name, self.pk))

    def update_total(self):
        self.total = sum([registration.price for registration in self.registrations.all()])

    def update_status(self):
        if self.status == 'waiting' and not self.registrations.exclude(status=Registration.STATUS.canceled)\
                                                              .filter(paid=False).exists():
            self.status = self.STATUS.paid

    def __unicode__(self):
        return self.billing_identifier


class ExtraInfo(models.Model):
    registration = models.ForeignKey('registrations.Registration', related_name='extra_infos',
                                     on_delete=models.CASCADE)
    key = models.ForeignKey('activities.ExtraNeed', on_delete=models.CASCADE)
    value = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ('key', 'registration')

    @property
    def price_modifier(self):
        return self.key.price_dict.get(self.value, 0)

    def save(self, *args, **kwargs):
        super(ExtraInfo, self).save(*args, **kwargs)
        self.registration.save()


class Child(TimeStampedModel, StatusModel):
    STATUS = Choices(
        ('updated', _("Updated")),
        ('imported', _("Imported")),
    )
    SEX = Choices(('M', _('Male')),
                  ('F', _('Female')),
                  )
    NATIONALITY = Choices(('CH', _('Swiss')),
                          ('FL', _('Liechtenstein')),
                          ('DIV', _('Other')),
                          )
    LANGUAGE = Choices(('D', 'Deutsch'),
                       ('E', 'English'),
                       ('F', u'Français'),
                       ('I', 'Italiano'),
                       )
    first_name = models.CharField(_("First name"), max_length=50)
    last_name = models.CharField(_("Last name"), max_length=50)
    sex = models.CharField(_("Sex"), max_length=1, choices=SEX)
    birth_date = models.DateField(_("Birth date"))
    nationality = models.CharField(choices=NATIONALITY, max_length=3, default=NATIONALITY.CH)
    language = models.CharField(choices=LANGUAGE, max_length=2, default=LANGUAGE.F)

    school_year = models.ForeignKey('profiles.SchoolYear', null=True, blank=True, on_delete=models.SET_NULL)
    building = models.ForeignKey('schools.Building', related_name="students", null=True, blank=True, on_delete=models.SET_NULL)
    teacher = models.ForeignKey('schools.Teacher', related_name="students", null=True, blank=True, on_delete=models.SET_NULL)

    family = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='children',
                               null=True, blank=True, on_delete=models.CASCADE)
    courses = models.ManyToManyField('activities.Course', through="registrations.Registration")

    id_lagapeo = models.IntegerField(db_index=True, unique=True, null=True, blank=True,
                                     verbose_name=_("Lagapeo Identification number"))

    emergency_number = PhoneNumberField(_("Emergency number"), max_length=30, blank=True)
    school = models.ForeignKey('profiles.School', related_name="students", null=True, blank=True, on_delete=models.SET_NULL)
    other_school = models.CharField(_("Other school"), blank=True, max_length=50)
    bib_number = models.CharField(_("Bib number"), blank=True, max_length=20)
    is_blacklisted = models.BooleanField(_("Is blacklisted"), default=False, db_index=True)

    class Meta:
        ordering = ('last_name', 'first_name',)
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
    def js_birth_date(self):
        return self.birth_date.strftime('%d.%m.%Y')

    @property
    def js_sex(self):
        if self.sex == self.SEX.M:
            return '1'
        return '2'

    @property
    def montreux_needs_appointment(self):
        for registration in self.registrations.all():
            if registration.extra_infos.filter(key__question_label__contains=u"matériel", value='OUI').exists():
                return True
        return False

    @property
    def ordering_name(self):
        return u'{} {}'.format(self.last_name.lower().strip(), self.first_name.lower().strip())

    @property
    def school_name(self):
        if self.school:
            return self.school.name
        else:
            return self.other_school

    @property
    def update_url(self):
        return self.get_update_url()

    def get_backend_absences_url(self):
        return reverse('backend:child-absences', kwargs={'child': self.pk})

    def get_backend_detail_url(self):
        return reverse('backend:child-detail', kwargs={'child': self.pk})

    def get_backend_url(self):
        if self.family:
            return reverse('backend:user-detail', kwargs={'pk': self.family.pk})
        return self.get_update_url()

    def get_delete_url(self):
        return reverse('backend:child-delete', kwargs={'child': self.pk})

    def get_full_name(self):
        full_name = u'%s %s' % (self.first_name.title(), self.last_name.title())
        return full_name.strip()

    def get_update_url(self):
        return reverse('backend:child-update', kwargs={'child': self.pk})

    def __unicode__(self):
        return self.get_full_name()


class ChildActivityLevel(TimeStampedModel):
    LEVELS = Choices(('NP', 'NP'),
                     ('CM', 'CM'),
                     ('ABS', 'ABS'),
                     ('NPA', 'NPA'),
                     ('NPB', 'NPB'),
                     ('NPC', 'NPC'),
                     ('A 1A', 'A 1A'),
                     ('A 1B', 'A 1B'),
                     ('A 1C', '1C'),
                     ('A 2A', '2A'),
                     ('A 2B', 'A 2B'),
                     ('A 2C', 'A 2C'),
                     ('A 3A', 'A 3A'),
                     ('A 3B', 'A 3B'),
                     ('A 3C', 'A 3C'),
                     ('A 4A', 'A 4A'),
                     ('A 4B', 'A 4B'),
                     ('A 4C', 'A 4C'),
                     ('A 5A', 'A 5A'),
                     ('A 5B', 'A 5B'),
                     ('A 5C', 'A 5C'),
                     ('A 6A', 'A 6A'),
                     ('A 6B', 'A 6B'),
                     ('A 6C', 'A 6C'),
                     ('A 7A', 'A 7A'),
                     ('A 7B', 'A 7B'),
                     ('A 7C', 'A 7C'),

                     ('S 1A', 'S 1A'),
                     ('S 1B', 'S 1B'),
                     ('S 1C', 'S 1C'),
                     ('S 2A', 'S 2A'),
                     ('S 2B', 'S 2B'),
                     ('S 2C', 'S 2C'),
                     ('S 3A', 'S 3A'),
                     ('S 3B', 'S 3B'),
                     ('S 3C', 'S 3C'),
                     ('S 4A', 'S 4A'),
                     ('S 4B', 'S 4B'),
                     ('S 4C', 'S 4C'),
                     ('S 5A', 'S 5A'),
                     ('S 5B', 'S 5B'),
                     ('S 5C', 'S 5C'),
                     ('S 6A', 'S 6A'),
                     ('S 6B', 'S 6B'),
                     ('S 6C', 'S 6C'),
                     ('S 7A', 'S 7A'),
                     ('S 7B', 'S 7B'),
                     ('S 7C', 'S 7C'),

                     )

    before_level = models.CharField(max_length=10, blank=True,
                                    verbose_name=_("Level -1"),)
    after_level = models.CharField(choices=LEVELS, max_length=5, blank=True,
                                   verbose_name=_("End course level"))
    note = models.CharField(max_length=50, verbose_name=_("Note"), blank=True)
    activity = models.ForeignKey('activities.Activity', related_name="levels", verbose_name=_("Course"),
                                 on_delete=models.CASCADE)
    child = models.ForeignKey('Child', related_name="levels", on_delete=models.CASCADE)

    class Meta:
        unique_together = ('activity', 'child')

    @property
    def api_url(self):
        return self.get_api_url()

    def get_api_url(self):
        return reverse('api:level-detail', kwargs={'pk': self.pk})


class RegistrationsProfile(TimeStampedModel):
    """
    This model acts as a cache to avoid useless comparisons
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='profile',
                                null=True, on_delete=models.SET_NULL)

    has_paid_all = models.BooleanField(default=False, blank=True, editable=False)
    finished_registering = models.BooleanField(default=False, blank=True, editable=False)
    last_registration = models.DateTimeField(null=True, blank=True, editable=False)

    def save(self, *args, **kwargs):
        self.has_paid_all = self.user.paid
        self.finished_registering = self.user.finished_registrations
        self.last_registration = self.user.last_registration
        super(RegistrationsProfile, self).save(*args, **kwargs)
