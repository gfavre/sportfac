# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from datetime import datetime, date

from django.core.urlresolvers import reverse
from django.db import models, transaction
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _

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
    STATUS = Choices(('waiting', _("Waiting parent's confirmation")),
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
    transport = models.ForeignKey('Transport', related_name='participants', null=True,
                                  verbose_name=_("Transport information"),
                                  on_delete=models.SET_NULL)

    objects = RegistrationManager()

    class Meta:
        unique_together = ('course', 'child', 'status')
        verbose_name = _("Registration")
        verbose_name_plural = _("Registrations")
        ordering = ('child__last_name', 'child__first_name', 'course__start_date')

    @property
    def extra_needs(self):
        return self.course.extra.all().exclude(id__in=self.extra_infos.values_list('key'))

    def is_valid(self):
        return self.extra_needs.count() == 0

    def __unicode__(self):
        return _(u'%(child)s ⇒ course %(number)s (%(activity)s)') % {
            'child': self.child.full_name,
            'number': self.course.number,
            'activity': self.course.activity.name
        }

    def set_waiting(self):
        self.status = self.STATUS.waiting

    def set_valid(self):
        self.status = self.STATUS.valid

    def set_confirmed(self):
        self.status = self.STATUS.confirmed

    def cancel(self):
        self.status = self.STATUS.canceled

    def overlap(self, r2):
        """Test if another registration object overlaps with this one."""
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

        interval = min(datetime.combine(date.today(), self.course.start_time) -
                       datetime.combine(date.today(), r2.course.end_time),
                       datetime.combine(date.today(), r2.course.start_time) -
                       datetime.combine(date.today(), self.course.end_time))

        if interval.days < 0:
            # overlap
            return True
        elif interval.seconds < (60 * 30):
            # less than half an hour between courses
            return True
        return False

    def get_delete_url(self):
        return reverse('backend:registration-delete', kwargs={'pk': self.pk})

    def get_update_url(self):
        return reverse('backend:registration-update', kwargs={'pk': self.pk})

    @property
    def update_url(self):
        return self.get_update_url()

    @property
    def delete_url(self):
        return self.get_delete_url()

    def save(self, *args, **kwargs):
        with transaction.atomic():
            super(Registration, self).save(*args, **kwargs)
            if self.bill:
                self.bill.save()

    def delete(self, *args, **kwargs):
        super(Registration, self).delete(*args, **kwargs)
        if self.bill:
            self.bill.save()


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
    STATUS = Choices(('just_created', _("Just created")),
                     ('waiting', _("Waiting parent's payment")),
                     ('paid', _("Paid by parent")),
                     ('canceled', _("Canceled by administrator")),
                     )
    billing_identifier = models.CharField(_('Billing identifier'), max_length=45, blank=True)
    family = models.ForeignKey('profiles.FamilyUser', verbose_name=_('User'), related_name='bills',
                               on_delete=models.CASCADE)
    total = models.PositiveIntegerField(default=0, verbose_name=_("Total to be paid"))

    objects = BillManager()

    def update_total(self):
        total = self.registrations.aggregate(models.Sum('course__price')).get('course__price__sum')
        self.total = total or 0

    def update_billing_identifier(self):
        if self.pk:
            self.billing_identifier = slugify('%s-%i' % (self.family.last_name, self.pk))

    def get_absolute_url(self):
        return reverse('registrations_bill_detail', kwargs={'pk': self.pk})

    def get_backend_url(self):
        return reverse('backend:bill-detail', kwargs={'pk': self.pk})

    def get_pay_url(self):
        return reverse('backend:bill-update', kwargs={'pk': self.pk})

    @property
    def is_ok(self):
        return self.status != self.STATUS.waiting

    @property
    def is_paid(self):
        return self.status in (self.STATUS.paid, self.STATUS.canceled)

    @property
    def backend_url(self):
        return self.get_backend_url()

    @property
    def pay_url(self):
        return self.get_pay_url()

    @transaction.atomic
    def close(self):
        self.status = self.STATUS.paid
        for registration in self.registrations.filter(status=Registration.STATUS.valid):
            registration.paid = True
            registration.save()

    @transaction.atomic
    def save(self, *args, **kwargs):
        self.update_total()
        if not self.billing_identifier:
            self.update_billing_identifier()
        super(Bill, self).save(*args, **kwargs)

    class Meta:
        verbose_name = _("Bill")
        verbose_name_plural = _("Bills")


class ExtraInfo(models.Model):
    registration = models.ForeignKey('registrations.Registration', related_name='extra_infos',
                                     on_delete=models.CASCADE)
    key = models.ForeignKey('activities.ExtraNeed', on_delete=models.CASCADE)
    value = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ('key', 'registration')


class Child(TimeStampedModel):
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

    family = models.ForeignKey('profiles.FamilyUser', related_name='children', null=True, blank=True, on_delete=models.CASCADE)
    courses = models.ManyToManyField('activities.Course', through="registrations.Registration")

    id_lagapeo = models.IntegerField(db_index=True, unique=True, null=True, blank=True,
                                     verbose_name=_("Lagapeo Identification number"))

    emergency_number = PhoneNumberField(_("Emergency number"), max_length=30, blank=True)
    school = models.ForeignKey('profiles.School', related_name="students", null=True, blank=True, on_delete=models.SET_NULL)
    other_school = models.CharField(_("Other school"), blank=True, max_length=50)
    bib_number = models.CharField(_("Bib number"), blank=True, max_length=20)

    class Meta:
        ordering = ('last_name', 'first_name',)
        abstract = False

    def get_update_url(self):
        return reverse('backend:child-update', kwargs={'child': self.pk})

    def get_delete_url(self):
        return reverse('backend:child-delete', kwargs={'child': self.pk})

    def get_backend_url(self):
        if self.family:
            return reverse('backend:user-detail', kwargs={'pk': self.family.pk})
        return self.get_update_url()

    def get_backend_detail_url(self):
        return reverse('backend:child-detail', kwargs={'child': self.pk})

    def get_backend_absences_url(self):
        return reverse('backend:child-absences', kwargs={'child': self.pk})

    def get_full_name(self):
        full_name = u'%s %s' % (self.first_name.title(), self.last_name.title())
        return full_name.strip()

    @property
    def full_name(self):
        return self.get_full_name()

    @property
    def ordering_name(self):
        return u'{} {}'.format(self.last_name.lower().strip(), self.first_name.lower().strip())

    @property
    def backend_url(self):
        return self.get_backend_url()

    @property
    def update_url(self):
        return self.get_update_url()

    @property
    def delete_url(self):
        return self.get_delete_url()

    @property
    def full_name(self):
        return self.get_full_name()

    @property
    def school_name(self):
        if self.school:
            return self.school.name
        else:
            return self.other_school

    @property
    def js_sex(self):
        if self.sex == self.SEX.M:
            return '1'
        return '2'

    @property
    def js_birth_date(self):
        return self.birth_date.strftime('%d.%m.%Y')

    def __unicode__(self):
        return self.get_full_name()

    class Meta:
        verbose_name = _("Child")
        verbose_name_plural = _("Children")


class ChildActivityLevel(TimeStampedModel):
    LEVELS = Choices(('NP', 'NP'),
                     ('CM', 'CM'),
                     ('ABS', 'ABS'),
                     ('NPA', 'NPA'),
                     ('NPB', 'NPB'),
                     ('NPC', 'NPC'),
                     ('1A', '1A'),
                     ('1B', '1B'),
                     ('1C', '1C'),
                     ('2A', '2A'),
                     ('2B', '2B'),
                     ('2C', '2C'),
                     ('3A', '3A'),
                     ('3B', '3B'),
                     ('3C', '3C'),
                     ('4A', '4A'),
                     ('4B', '4B'),
                     ('4C', '4C'),
                     ('5A', '5A'),
                     ('5B', '5B'),
                     ('5C', '5C'),
                     ('6A', '6A'),
                     ('6B', '6B'),
                     ('6C', '6C'),
                     ('7A', '7A'),
                     ('7B', '7B'),
                     ('7C', '7C'),
                     )

    before_level = models.CharField(choices=LEVELS, max_length=5, blank=True,
                                    verbose_name=_("Level -1"),)
    after_level = models.CharField(choices=LEVELS, max_length=5, blank=True,
                                   verbose_name=_("End course level"))
    note = models.CharField(max_length=50, verbose_name=_("Note"), blank=True)
    activity = models.ForeignKey('activities.Activity', related_name="levels", verbose_name=_("Course"),
                                 on_delete=models.CASCADE)
    child = models.ForeignKey('Child', related_name="levels", on_delete=models.CASCADE)

    class Meta:
        unique_together = ('activity', 'child')

    def get_api_url(self):
        return reverse('api:level-detail', kwargs={'pk': self.pk})

    @property
    def api_url(self):
        return self.get_api_url()
