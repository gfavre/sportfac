# -*- coding: utf-8 -*-
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db import models, connection
from django.db.models.aggregates import Count, Sum
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.template.defaultfilters import date as _date
from django.utils.translation import ugettext_lazy as _

from autoslug import AutoSlugField
from ckeditor_uploader.fields import RichTextUploadingField
from dateutil.relativedelta import relativedelta
from model_utils import Choices

from sportfac.models import TimeStampedModel
from .utils import course_to_js_csv

DAYS_OF_WEEK = (
    (1, _('Monday')),
    (2, _('Tuesday')),
    (3, _('Wednesday')),
    (4, _('Thursday')),
    (5, _('Friday')),
    (6, _('Saturday')),
    (7, _('Sunday')),
)

SCHOOL_YEARS = (
    (1, _("1P")),
    (2, _("2P")),
    (3, _("3P")),
    (4, _("4P")),
    (5, _("5P")),
    (6, _("6P")),
    (7, _("7P")),
    (8, _("8P")),
    (9, _("9S")),
    (10, _("10S")),
    (11, _("11S")),
    (12, _("12S")),
)

AGES = Choices(
    *[(age, 'a{}'.format(age), _('%i years old') % age) for age in settings.KEPCHUP_AGES]
)


class ActivityManager(models.Manager):
    def visible(self):
        return self.get_queryset().filter(courses__visible=True).annotate(count=Count('courses')).filter(count__gt=0)


class Activity(TimeStampedModel):
    """
    An activity
    """
    name = models.CharField(max_length=50, db_index=True, unique=True, verbose_name=_("Name"))
    type = models.CharField(max_length=50, db_index=True, verbose_name=_("Type"),
                            choices=settings.KEPCHUP_ACTIVITY_TYPES,
                            default=settings.KEPCHUP_ACTIVITY_TYPES[0][0])
    number = models.CharField(max_length=30,
                              db_index=True, unique=True,
                              null=True, blank=True,
                              verbose_name=_("Identifier"))
    slug = AutoSlugField(populate_from='name', max_length=50, db_index=True, unique=True,
                         help_text=_("Part of the url. Cannot contain punctuation, spaces or accentuated letters"))
    informations = RichTextUploadingField(verbose_name=_("Informations"), blank=True,
                                          help_text=_("Specific informations like outfit."))
    description = RichTextUploadingField(verbose_name=_("Description"), blank=True)
    allocation_account = models.ForeignKey('AllocationAccount', null=True, blank=True, related_name='activities',
                                           verbose_name=_("Allocation account"))
    objects = ActivityManager()

    class Meta:
        ordering = ['name']
        verbose_name = _("activity")
        verbose_name_plural = _("activities")

    @property
    def backend_absences_url(self):
        return reverse('backend:activity-absences', kwargs={'activity': self.slug})

    @property
    def backend_url(self):
        return self.get_backend_url()

    @property
    def delete_url(self):
        return self.get_delete_url()

    @property
    def participants(self):
        from registrations.models import Registration
        return Registration.objects.filter(course__in=self.courses.all())

    @property
    def update_url(self):
        return self.get_update_url()

    def get_absolute_url(self):
        return reverse('activities:activity-detail', kwargs={"slug": self.slug})

    def get_backend_url(self):
        return reverse('backend:activity-detail', kwargs={'activity': self.slug})

    def get_delete_url(self):
        return reverse('backend:activity-delete', kwargs={'activity': self.slug})

    def get_update_url(self):
        return reverse('backend:activity-update', kwargs={'activity': self.slug})

    def __unicode__(self):
        return self.name


class AllocationAccount(TimeStampedModel):
    account = models.CharField(max_length=50, verbose_name=_("Account"),
                               help_text=_("e.g. 154.4652.00"),
                               unique=True, )
    name = models.CharField(max_length=50, verbose_name=_("Name"), blank=True,
                            help_text=_("Some text to help humans filter account numbers"))

    class Meta:
        ordering = ['account']
        verbose_name = _("Allocation account")
        verbose_name_plural = _("Allocation accounts")

    def __unicode__(self):
        if self.name:
            return u'{} {}'.format(self.account, self.name)
        return self.account

    def get_backend_url(self):
        return reverse('backend:allocation-update', kwargs={'pk': self.pk})

    def get_update_url(self):
        return reverse('backend:allocation-update', kwargs={'pk': self.pk})

    def get_delete_url(self):
        return reverse('backend:allocation-delete', kwargs={'pk': self.pk})

    def get_registrations(self, start=None, end=None, **kwargs):
        if start:
            kwargs['created__gte'] = start
        if end:
            kwargs['created__lte'] = datetime.combine(end, time.max)
        return (self.registrations.filter(**kwargs).prefetch_related('bill__datatrans_transactions')) \
            .select_related('course', 'course__activity', 'bill').order_by('created')

    def get_total_transactions(self, period_start=None, period_end=None):
        return self.registrations.all().aggregate(Sum('price'))['price__sum']


class CourseManager(models.Manager):
    def visible(self):
        return self.get_queryset().filter(visible=True)

    def camps(self):
        return self.get_queryset().filter(type=Course.TYPE.camp)


class Course(TimeStampedModel):
    """A course, i.e. an instance of an activity"""
    TYPE = Choices(
        ('course', _("Course (single day per week)")),
        ('multicourse', _("Course (multiple days per week)")),
        ('camp', _("Camp")),

    )
    activity = models.ForeignKey('Activity', related_name='courses',
                                 verbose_name=_("Activity"))
    course_type = models.CharField(_("Course type"), max_length=16, choices=TYPE, default=TYPE.course)
    number = models.CharField(max_length=30,
                              db_index=True, unique=True,
                              null=True, blank=True,
                              verbose_name=_("Identifier"))
    name = models.CharField(null=True, blank=True, max_length=50,
                            verbose_name=_("Displayed name"))
    comments = RichTextUploadingField(verbose_name=_("Comments"), blank=True)

    uptodate = models.BooleanField(verbose_name=_("Course up to date"), default=True)
    visible = models.BooleanField(verbose_name=_("Course visible"), default=True)

    instructors = models.ManyToManyField('profiles.FamilyUser', verbose_name=_("Instructors"),
                                         related_name='course', through='CoursesInstructors')

    local_city_override = models.ManyToManyField(to='profiles.City', verbose_name=_("Local city override"), null=True, blank=True)
    price = models.DecimalField(max_digits=5, decimal_places=2, verbose_name=_("Price"), null=True, blank=True)
    price_local = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                      verbose_name=_("Price for local people"))
    price_family = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name=_("Price for family members"),
        help_text=_("Applied for the second and following members registered to the same course"),
    )
    price_local_family = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name=_("Price for local family members"),
        help_text=_("Applied for the second and following members registered to the same course if the "
                            "family is local"),
    )
    price_description = models.TextField(_("Informations about pricing"), blank=True)

    number_of_sessions = models.PositiveSmallIntegerField(verbose_name=_("Number of sessions"), default=0)
    day = models.PositiveSmallIntegerField(choices=DAYS_OF_WEEK, verbose_name=_("Day"), default=1, blank=True)
    start_date = models.DateField(verbose_name=_("Start date"), null=True)
    end_date = models.DateField(verbose_name=_("End date"), null=True)
    start_time = models.TimeField(verbose_name=_("Start time"), null=True, blank=True)
    end_time = models.TimeField(verbose_name=_("End time"), null=True, blank=True)

    start_time_mon = models.TimeField(verbose_name=_("Start time, mondays"), null=True, blank=True)
    end_time_mon = models.TimeField(verbose_name=_("End time, mondays"), null=True, blank=True)
    start_time_tue = models.TimeField(verbose_name=_("Start time, tuesdays"), null=True, blank=True)
    end_time_tue = models.TimeField(verbose_name=_("End time, tuesdays"), null=True, blank=True)
    start_time_wed = models.TimeField(verbose_name=_("Start time, wednesdays"), null=True, blank=True)
    end_time_wed = models.TimeField(verbose_name=_("End time, wednesdays"), null=True, blank=True)
    start_time_thu = models.TimeField(verbose_name=_("Start time, thursdays"), null=True, blank=True)
    end_time_thu = models.TimeField(verbose_name=_("End time, thursdays"), null=True, blank=True)
    start_time_fri = models.TimeField(verbose_name=_("Start time, fridays"), null=True, blank=True)
    end_time_fri = models.TimeField(verbose_name=_("End time, fridays"), null=True, blank=True)
    start_time_sat = models.TimeField(verbose_name=_("Start time, saturdays"), null=True, blank=True)
    end_time_sat = models.TimeField(verbose_name=_("End time, saturdays"), null=True, blank=True)
    start_time_sun = models.TimeField(verbose_name=_("Start time, sundays"), null=True, blank=True)
    end_time_sun = models.TimeField(verbose_name=_("End time, sundays"), null=True, blank=True)

    place = models.TextField(verbose_name=_("Place"))
    nb_participants = models.SmallIntegerField(verbose_name=_("Current nb of participants"), default=0)
    min_participants = models.PositiveSmallIntegerField(verbose_name=_("Minimal number of participants"))
    max_participants = models.PositiveSmallIntegerField(verbose_name=_("Maximal number of participants"))

    schoolyear_min = models.PositiveIntegerField(choices=SCHOOL_YEARS,
                                                 verbose_name=_("Minimal school year"), blank=True, null=True)
    schoolyear_max = models.PositiveIntegerField(choices=SCHOOL_YEARS,
                                                 verbose_name=_("Maximal school year"), blank=True, null=True)

    age_min = models.PositiveIntegerField(choices=AGES,
                                          verbose_name=_("Minimal age"), help_text=_("At the beginning of course"),
                                          blank=True, null=True)
    age_max = models.PositiveIntegerField(choices=AGES,
                                          verbose_name=_("Maximal age"), help_text=_("At the beginning of course"),
                                          blank=True, null=True)
    min_birth_date = models.DateField(verbose_name=_("Minimal birth date to register"), null=True, editable=False)
    max_birth_date = models.DateField(verbose_name=_("Maximal birth date to register"), null=True, editable=False)

    announced_js = models.BooleanField(_("Course announced to J+S"), default=False)

    objects = CourseManager()

    class Meta:
        ordering = ('activity__name', 'number',)
        verbose_name = _("course")
        verbose_name_plural = _("courses")

    @property
    def ages(self):
        return range(self.age_min or settings.KEPCHUP_AGES[0], (self.age_max or settings.KEPCHUP_AGES[-1]) + 1)

    @property
    def ages_label(self):
        return [dict(AGES)[age] for age in self.ages]

    @property
    def available_places(self):
        return self.max_participants - self.count_participants

    @property
    def backend_absences_url(self):
        return self.get_backend_absences_url()

    @property
    def backend_url(self):
        return self.get_backend_url()

    @property
    def count_participants(self):
        return self.nb_participants

    @property
    def day_name(self):
        days = dict(DAYS_OF_WEEK)
        if self.is_camp:
            return unicode(days[self.start_date.isoweekday()]) + u' - ' + unicode(days[self.end_date.isoweekday()])
        return unicode(dict(DAYS_OF_WEEK).get(self.day, str(self.day)))

    @property
    def days_names(self):
        days = dict(DAYS_OF_WEEK)
        out = []
        if self.start_time_mon:
            out.append(unicode(days[1]))
        if self.start_time_tue:
            out.append(unicode(days[2]))
        if self.start_time_wed:
            out.append(unicode(days[3]))
        if self.start_time_thu:
            out.append(unicode(days[4]))
        if self.start_time_fri:
            out.append(unicode(days[5]))
        if self.start_time_sat:
            out.append(unicode(days[6]))
        if self.start_time_sun:
            out.append(unicode(days[7]))
        return out

    @property
    def delete_url(self):
        return self.get_delete_url()

    @property
    def duration(self):
        if self.is_camp:
            if settings.KEPCHUP_EXPLICIT_SESSION_DATES:
                if self.sessions.exists():
                    return self.sessions.last().date + timedelta(days=1) - self.sessions.first().date
                return None
            else:
                return (self.end_date - self.start_date) + timedelta(days=1)
        elif self.is_multi_course:
            return max([
                datetime.combine(date.today(), self.end_time_mon or time(0, 0)) - datetime.combine(date.today(), self.start_time_mon or time(0, 0)),
                datetime.combine(date.today(), self.end_time_tue or time(0, 0)) - datetime.combine(date.today(), self.start_time_tue or time(0, 0)),
                datetime.combine(date.today(), self.end_time_wed or time(0, 0)) - datetime.combine(date.today(), self.start_time_wed or time(0, 0)),
                datetime.combine(date.today(), self.end_time_thu or time(0, 0)) - datetime.combine(date.today(), self.start_time_thu or time(0, 0)),
                datetime.combine(date.today(), self.end_time_fri or time(0, 0)) - datetime.combine(date.today(), self.start_time_fri or time(0, 0)),
                datetime.combine(date.today(), self.end_time_sat or time(0, 0)) - datetime.combine(date.today(), self.start_time_sat or time(0, 0)),
                datetime.combine(date.today(), self.end_time_sun or time(0, 0)) - datetime.combine(date.today(), self.start_time_sun or time(0, 0)),])
        return datetime.combine(date.today(), self.end_time or time(23, 59)) - datetime.combine(date.today(), self.start_time or time(0, 0))

    @property
    def full(self):
        return self.count_participants >= self.max_participants

    @property
    def get_js_name(self):
        return '%s - %s' % (self.number, self.activity.name)

    @property
    def has_issue(self):
        return self.count_participants > self.max_participants

    @property
    def has_participants(self):
        return self.participants.exists()

    @property
    def start_hours(self):
        out = []
        if self.start_time_mon:
            out.append(self.start_time_mon)
        if self.start_time_tue:
            out.append(self.start_time_tue)
        if self.start_time_wed:
            out.append(self.start_time_wed)
        if self.start_time_thu:
            out.append(self.start_time_thu)
        if self.start_time_fri:
            out.append(self.start_time_fri)
        if self.start_time_sat:
            out.append(self.start_time_sat)
        if self.start_time_sun:
            out.append(self.start_time_sun)
        return out

    @property
    def is_course(self):
        return self.course_type == self.TYPE.course

    @property
    def is_camp(self):
        return self.course_type == self.TYPE.camp

    @property
    def is_multi_course(self):
        return self.course_type == self.TYPE.multicourse

    @property
    def last_convocation_email(self):
        receipt = self.email_receipts.filter(type=TemplatedEmailReceipt.TYPE.convocation).order_by('modified').last()
        if receipt:
            return receipt.modified
        return None

    @property
    def last_instructor_email(self):
        receipt = self.email_receipts.filter(type=TemplatedEmailReceipt.TYPE.instructors).order_by('modified').last()
        if receipt:
            return receipt.modified
        return None

    @property
    def long_name(self):
        if self.name:
            return u'{} - {}'.format(self.short_name, self.name)
        return self.short_name

    @property
    def minimal_participants_reached(self):
        return self.count_participants >= self.min_participants

    @property
    def percentage_full(self):
        try:
            return int(100 * float(self.count_participants) / float(self.max_participants))
        except ZeroDivisionError:
            return 100

    @property
    def school_years(self):
        if self.schoolyear_min and self.schoolyear_max:
            return range(self.schoolyear_min, self.schoolyear_max + 1)
        return []

    @property
    def school_years_label(self):
        return [dict(SCHOOL_YEARS)[year] for year in self.school_years]

    @property
    def short_name(self):
        return '%s (%s)' % (self.activity.name, self.number)

    @property
    def update_url(self):
        return self.get_update_url()

    def add_session(self, date, instructor=None):
        from absences.models import Session
        if settings.KEPCHUP_ABSENCES_RELATE_TO_ACTIVITIES:
            session, created = Session.objects.get_or_create(course=self,
                                                             date=date,
                                                             defaults={'instructor': instructor,
                                                                       'activity': self.activity})
        else:
            session, created = Session.objects.get_or_create(course=self,
                                                             date=date,
                                                             defaults={'instructor': instructor})
        session.fill_absences()
        session.update_courses_dates()
        return session

    def detailed_label(self):
        base = unicode(self)
        if self.is_course:
            dates = _(u'from %(start)s to %(end)s, every %(day)s at %(hour)s.')
            return base + ', ' + dates % {
                'start': self.start_date and self.start_date.strftime("%d/%m/%Y"),
                'end': self.end_date and self.end_date.strftime("%d/%m/%Y"),
                'day': self.day_name.lower(),
                'hour': self.start_time.strftime("%H:%M"),
            }
        elif self.is_camp:
            return base + ', {}-{}'.format(self.start_date.strftime("%d/%m/%Y"), self.end_date.strftime("%d/%m/%Y"))
        return base

    def get_absences_url(self):
        return reverse('activities:course-absence', kwargs={'course': self.pk})

    def get_absolute_url(self):
        return reverse('activities:course-detail', kwargs={"course": self.pk})

    def get_backend_absences_url(self):
        if settings.KEPCHUP_ABSENCES_RELATE_TO_ACTIVITIES:
            return reverse('backend:activity-absences',
                           kwargs={'activity': self.activity.slug}) + '?c={}'.format(self.pk)
        return reverse('backend:course-absence', kwargs={'course': self.pk})

    def get_custom_mail_custom_users_instructors_url(self):
        return reverse('activities:mail-custom-participants-custom', kwargs={'course': self.pk})

    def get_backend_url(self):
        return reverse('backend:course-detail', kwargs={'course': self.pk})

    def get_custom_mail_url(self):
        return reverse('backend:mail-participants-custom', kwargs={'course': self.pk})

    def get_custom_mail_instructors_url(self):
        return reverse('activities:mail-participants-custom', kwargs={'course': self.pk})

    def get_delete_url(self):
        return reverse('backend:course-delete', kwargs={'course': self.pk})

    def get_duplicate_url(self):
        return reverse('backend:course-create') + '?source={}'.format(self.pk)


    def get_js_export_url(self):
        return reverse('backend:course-js-export', kwargs={'course': self.pk})

    def get_js_csv(self, filelike):
        course_to_js_csv(self, filelike)

    def get_mail_instructors_url(self):
        return reverse('backend:course-mail-instructors', kwargs={'course': self.pk})

    def get_mail_infos_url(self):
        return reverse('activities:mail-instructors', kwargs={'course': self.pk})

    def get_mail_confirmation_url(self):
        return reverse('backend:course-mail-confirmation', kwargs={'course': self.pk})

    def get_period_text(self):
        if self.start_date.year == self.end_date.year:
            if self.start_date.month == self.end_date.month:
                return _date(self.start_date, 'F Y')
            else:
                return _date(self.start_date, 'F') + ' - ' + _date(self.end_date, 'F Y')
        else:
            return _date(self.start_date, 'F Y') + ' - ' + _date(self.end_date, 'F Y')

    def get_sessions(self):
        return self.sessions.all()

    def get_update_url(self):
        return reverse('backend:course-update', kwargs={'course': self.pk})

    def get_xls_export_url(self):
        return reverse('backend:course-xls-export', kwargs={'course': self.pk})

    def save(self, *args, **kwargs):
        if settings.KEPCHUP_EXPLICIT_SESSION_DATES:
            self.update_dates_from_sessions(commit=False)
        if self.age_min and self.start_date:
            self.min_birth_date = self.start_date - relativedelta(years=self.age_min)
        if self.age_max and self.start_date:
            # if we say up to 6 years old, we want to include children of 6 1/2 years old, hence the +1
            self.max_birth_date = self.start_date - relativedelta(years=self.age_max + 1)
        self.update_nb_participants()
        super(Course, self).save(*args, **kwargs)

    def update_dates_from_sessions(self, commit=True):
        dates = self.sessions.values_list('date', flat=True)
        if len(dates):
            self.start_date = min(dates)
            self.end_date = max(dates)
            self.day = self.start_date.isoweekday()
            self.number_of_sessions = len(dates)
        else:
            self.start_date = None
            self.end_date = None
            self.number_of_sessions = 0
        if commit:
            self.save()

    def update_nb_participants(self):
        self.nb_participants = self.participants.count()

    def __unicode__(self):
        base = u'%(invisible)s%(activity)s (%(number)s): %(fullness)s'
        if self.full:
            fullness = _('Course full')
        else:
            fullness = _('%(available)s out of %(total)s places remaining') % {
                'available': self.available_places,
                'total': self.max_participants
            }
        return base % {
            'invisible': not self.visible and _("Invisible") + ' - ' or '',
            'activity': self.activity.name,
            'number': self.number,
            'fullness': fullness
        }


class CoursesInstructors(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    instructor = models.ForeignKey('profiles.FamilyUser', on_delete=models.CASCADE)
    function = models.ForeignKey('payroll.Function', on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ('course', 'instructor')


EXTRA_TYPES = (('B', _("Boolean")),
               ('C', _('Characters')),
               ('I', _("Integer")))


class ExtraNeed(TimeStampedModel):
    courses = models.ManyToManyField('Course', related_name='extra', blank=True)

    question_label = models.CharField(max_length=255, verbose_name=_("Question"),
                                      help_text=_("e.g. Shoes size?"))
    extra_info = models.TextField(blank=True)
    mandatory = models.BooleanField(default=True)
    type = models.CharField(verbose_name=_("Type of answer"),
                            choices=EXTRA_TYPES,
                            default='C',
                            max_length=2)
    choices = ArrayField(
        verbose_name=_("Limit to values (internal name, display name),(internal name 2, display name 2)"),
        base_field=models.CharField(max_length=255),
        blank=True,
        null=True)
    price_modifier = ArrayField(verbose_name=_("Modify price by xx francs if this value is selected"),
                                help_text=_("List of positive/negative values"),
                                base_field=models.IntegerField(),
                                blank=True,
                                null=True)
    default = models.CharField(verbose_name=_("Default value"), default="", blank=True, max_length=255)

    class Meta:
        verbose_name = _("extra question")
        verbose_name_plural = _("extra questions")

    @property
    def price_dict(self):
        if not self.price_modifier:
            return {}
        return dict(zip(self.choices, self.price_modifier))

    def __unicode__(self):
        if self.choices:
            out = '%s (%s)' % (self.question_label, ', '.join(self.choices))
            if self.price_modifier:
                out += ' - (' + ', '.join([str(price) for price in self.price_modifier]) + ')'
            return out
        return self.question_label


RATE_MODES = Choices(
    ('day', _("Daily")),
    ('hour', _("Hourly"))
)


class PaySlip(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instructor = models.ForeignKey('profiles.FamilyUser', verbose_name=_("Instructor"), on_delete=models.CASCADE)
    course = models.ForeignKey('Course', verbose_name=_("Course"), on_delete=models.CASCADE)
    rate = models.DecimalField(_("Rate"), max_digits=6, decimal_places=2)
    rate_mode = models.CharField(_("Rate mode"), max_length=10, choices=RATE_MODES, default=RATE_MODES.hour)
    start_date = models.DateField(_("Start date"))
    end_date = models.DateField(_("End date"))
    function = models.CharField(_("Function"), max_length=255)

    class Meta:
        # Let's see this another time and save too often...
        # unique_together = ('instructor', 'course')
        ordering = ('-created',)

    @property
    def amount(self):
        if self.rate_mode == RATE_MODES.hour:
            duration = self.course.duration
            hours = Decimal(duration.seconds / 3600.0 + duration.days * 24)
            return Decimal(self.rate) * Decimal(self.sessions.count()) * hours
        else:
            return Decimal(self.sessions.count()) * self.rate

    @property
    def average_presentees(self):
        return round(float(self.total_presentees) / max(len(self.sessions), 1), 1)

    @property
    def sessions(self):
        return self.course.sessions.filter(instructor=self.instructor,
                                           date__gte=self.start_date, date__lte=self.end_date)

    @property
    def total_presentees(self):
        return sum([session.presentees_nb() for session in self.sessions])

    def get_absolute_url(self):
        return reverse('activities:payslip-detail', kwargs={'pk': self.pk})


class TemplatedEmailReceipt(TimeStampedModel):
    TYPE = Choices(
        ('convocation', _("Convocation to the course")),
        ('need_confirmation', _("Need parent confirmation")),
        ('not_paid', _("Payment reminder")),
        ('instructors', _("Documents for course instructor")),
    )
    type = models.CharField(_("Email type"),

                            choices=TYPE, max_length=30)
    course = models.ForeignKey('Course', related_name='email_receipts', null=True, blank=True)

    class Meta:
        ordering = ('-created',)


def _invalidate_course_data(pk):
    tenant_pk = connection.get_tenant().pk
    cache_key = "tenant_{}_course_{}".format(tenant_pk, pk)
    cache.delete(cache_key)


@receiver(post_save, sender=Course, dispatch_uid='invalidate_course_data')
def course_post_save_handler(sender, instance, created, **kwargs):
    if not created:
        _invalidate_course_data(instance.id)


@receiver(post_delete, sender=Course, dispatch_uid='invalidate_course_data')
def course_post_delete_handler(sender, instance, **kwargs):
    _invalidate_course_data(instance.id)
