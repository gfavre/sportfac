# -*- coding: utf-8 -*-
from datetime import datetime, date

from django.contrib.postgres.fields import ArrayField
from django.conf import settings
from django.db import models
from django.db.models.aggregates import Count
from django.core.urlresolvers import reverse
from django.template.defaultfilters import date as _date
from django.utils.translation import ugettext_lazy as _, ugettext

from ckeditor_uploader.fields import RichTextUploadingField
from autoslug import AutoSlugField

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


class ActivityManager(models.Manager):
    def visible(self):
        return self.get_queryset().filter(courses__visible=True).annotate(count=Count('courses')).filter(count__gt=0)


class Activity(TimeStampedModel):
    """
    An activity
    """
    name = models.CharField(max_length=50, db_index=True, unique=True, verbose_name=_("Name"))
    number = models.CharField(max_length=30,
                              db_index=True, unique=True,
                              null=True, blank=True,
                              verbose_name=_("Identifier"))
    slug = AutoSlugField(populate_from='name', max_length=50, db_index=True, unique=True,
                         help_text=_("Part of the url. Cannot contain punctuation, spaces or accentuated letters"))
    informations = RichTextUploadingField(verbose_name=_("Informations"), blank=True,
                                          help_text=_("Specific informations like outfit."))
    description = RichTextUploadingField(verbose_name=_("Description"), blank=True)

    objects = ActivityManager()

    def get_absolute_url(self):
        return reverse('activities:activity-detail', kwargs={"slug": self.slug})

    def get_update_url(self):
        return reverse('backend:activity-update', kwargs={'activity': self.slug})

    def get_delete_url(self):
        return reverse('backend:activity-delete', kwargs={'activity': self.slug})

    def get_backend_url(self):
        return reverse('backend:activity-detail', kwargs={'activity': self.slug})

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
    def backend_absences_url(self):
        return reverse('backend:activity-absences', kwargs={'activity': self.slug})

    @property
    def participants(self):
        from registrations.models import Registration
        return Registration.objects.filter(course__in=self.courses.all())

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = _("activity")
        verbose_name_plural = _("activities")


class CourseManager(models.Manager):
    def visible(self):
        return self.get_queryset().filter(visible=True)


class Course(TimeStampedModel):
    """A course, i.e. an instance of an activity"""
    activity = models.ForeignKey('Activity', related_name='courses',
                                 verbose_name=_("Activity"))
    number = models.CharField(max_length=30,
                              db_index=True, unique=True,
                              null=True, blank=True,
                              verbose_name=_("Identifier"))
    name = models.CharField(null=True, blank=True, max_length=50,
                            verbose_name=_("Displayed name"))
    uptodate = models.BooleanField(verbose_name=_("Course up to date"), default=True)
    visible = models.BooleanField(verbose_name=_("Course visible"), default=True)

    instructors = models.ManyToManyField('profiles.FamilyUser', verbose_name=_("Instructors"), related_name='course')

    price = models.DecimalField(max_digits=5, decimal_places=2,
                                verbose_name=_("Price"),
                                null=True, blank=True)
    price_description = models.TextField(_("Informations about pricing"), blank=True)
    number_of_sessions = models.PositiveSmallIntegerField(verbose_name=_("Number of sessions"))
    day = models.PositiveSmallIntegerField(choices=DAYS_OF_WEEK, verbose_name=_("Day"), default=1, blank=True)
    start_date = models.DateField(verbose_name=_("Start date"))
    end_date = models.DateField(verbose_name=_("End date"))
    start_time = models.TimeField(verbose_name=_("Start time"))
    end_time = models.TimeField(verbose_name=_("End time"))
    place = models.TextField(verbose_name=_("Place"))
    min_participants = models.PositiveSmallIntegerField(verbose_name=_("Minimal number of participants"))
    max_participants = models.PositiveSmallIntegerField(verbose_name=_("Maximal number of participants"))
    schoolyear_min = models.PositiveIntegerField(choices=SCHOOL_YEARS, default="1", verbose_name=_("Minimal school year"))
    schoolyear_max = models.PositiveIntegerField(choices=SCHOOL_YEARS, default="12", verbose_name=_("Maximal school year"))

    announced_js = models.BooleanField(_("Course announced to J+S"), default=False)

    objects = CourseManager()

    class Meta:
        ordering = ('activity__name', 'number', )
        verbose_name = _("course")
        verbose_name_plural = _("courses")

    def get_sessions(self):
        return self.sessions.all()

    def add_session(self, date, instructor=None):
        from absences.models import Session
        if settings.KEPCHUP_ABSENCES_RELATE_TO_ACTIVITIES:
            session, created = Session.objects.get_or_create(activity=self.activity,
                                                             course=self,
                                                             date=date,
                                                             defaults={'instructor': instructor})
        else:
            session, created = Session.objects.get_or_create(course=self,
                                                             date=date,
                                                             defaults={'instructor': instructor})
        return session

    @property
    def day_name(self):
        return unicode(dict(DAYS_OF_WEEK).get(self.day, str(self.day)))

    @property
    def duration(self):
        return datetime.combine(date.today(), self.end_time) - datetime.combine(date.today(), self.start_time)

    @property
    def available_places(self):
        return self.max_participants - self.count_participants

    @property
    def count_participants(self):
        try:
            return self.nb_participants
        except AttributeError:
            return self.participants.count()

    @property
    def percentage_full(self):
        try:
            return int(100 * float(self.count_participants) / float(self.max_participants))
        except ZeroDivisionError:
            return 100

    @property
    def minimal_participants_reached(self):
        return self.count_participants >= self.min_participants

    @property
    def full(self):
        return self.count_participants >= self.max_participants

    @property
    def school_years(self):
        return range(self.schoolyear_min, self.schoolyear_max + 1)

    @property
    def school_years_label(self):
        return [dict(SCHOOL_YEARS)[year] for year in self.school_years]

    @property
    def short_name(self):
        return '%s (%s)' % (self.activity.name, self.number)

    @property
    def long_name(self):
        if self.name:
            return u'{} - {}'.format(self.short_name, self.name)
        return self.short_name

    def __unicode__(self):
        base = _(u'%(invisible)s%(activity)s (%(number)s): from %(start)s to %(end)s, every %(day)s at %(hour)s.')
        base %= {'invisible': not self.visible and _("Invisible") + ' - ' or '',
                 'activity': self.activity.name,
                 'number': self.number,
                 'start': self.start_date.strftime("%d/%m/%Y"),
                 'end': self.end_date.strftime("%d/%m/%Y"),
                 'day': self.day_name.lower(),
                 'hour': self.start_time.strftime("%H:%M"),
                 }
        return base

    def detailed_label(self):
        base = unicode(self)
        if self.full:
            fullness = ugettext('Course full')
        else:
            fullness = ugettext('%(available)s out of %(total)s places remaining')
            fullness %= {'available': self.available_places, 'total': self.max_participants}
        return base + ' ' + fullness

    def get_update_url(self):
        return reverse('backend:course-update', kwargs={'course': self.pk})

    def get_delete_url(self):
        return reverse('backend:course-delete', kwargs={'course': self.pk})

    def get_backend_url(self):
        return reverse('backend:course-detail', kwargs={'course': self.pk})

    def get_custom_mail_url(self):
        return reverse('backend:mail-participants-custom', kwargs={'course': self.pk})

    def get_custom_mail_instructors_url(self):
        return reverse('activities:mail-participants-custom', kwargs={'course': self.pk})

    def get_custom_mail_custom_users_instructors_url(self):
        return reverse('activities:mail-custom-participants-custom', kwargs={'course': self.pk})

    def get_mail_instructors_url(self):
        return reverse('backend:course-mail-instructors', kwargs={'course': self.pk})

    def get_mail_infos_url(self):
        return reverse('activities:mail-instructors', kwargs={'course': self.pk})

    def get_mail_confirmation_url(self):
        return reverse('backend:course-mail-confirmation', kwargs={'course': self.pk})

    def get_absences_url(self):
        return reverse('activities:course-absence', kwargs={'course': self.pk})

    def get_backend_absences_url(self):
        if settings.KEPCHUP_ABSENCES_RELATE_TO_ACTIVITIES:
            return reverse('backend:activity-absences',
                           kwargs={'activity': self.activity.slug}) + '?c={}'.format(self.pk)
        return reverse('backend:course-absence', kwargs={'course': self.pk})

    def get_js_export_url(self):
        return reverse('backend:course-js-export', kwargs={'course': self.pk})

    def get_xls_export_url(self):
        return reverse('backend:course-xls-export', kwargs={'course': self.pk})

    def get_js_csv(self, filelike):
        course_to_js_csv(self, filelike)

    @property
    def get_js_name(self):
        return '%s - %s' % (self.number, self.activity.name)

    def get_absolute_url(self):
        return reverse('activities:course-detail', kwargs={"course": self.pk})

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
    def backend_absences_url(self):
        return self.get_backend_absences_url()

    def get_period_text(self):
        if self.start_date.year == self.end_date.year:
            if self.start_date.month == self.end_date.month:
                return _date(self.start_date, 'F Y')
            else:
                return _date(self.start_date, 'F') + ' - ' + _date(self.end_date, 'F Y')
        else:
            return _date(self.start_date, 'F Y') + ' - ' + _date(self.end_date, 'F Y')

    def update_dates_from_sessions(self, commit=True):
        dates = self.sessions.values_list('date', flat=True)
        self.start_date = min(dates)
        self.end_date = max(dates)
        self.day = self.start_date.isoweekday()
        if commit:
            self.save()

    def save(self, *args, **kwargs):
        super(Course, self).save(*args, **kwargs)
        for instructor in self.instructors.all():
            instructor.is_instructor = True




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
    choices = ArrayField(verbose_name=_("Limit to values (internal name, display name),(internal name 2, display name 2)"),
                         base_field=models.CharField(max_length=255),
                         blank=True,
                         null=True)
    price_reduction = ArrayField(verbose_name=_("reduce price by xx francs if this value is selected"),
                                 base_field=models.IntegerField(),
                                 blank=True,
                                 null=True)
    default = models.CharField(verbose_name=_("Default value"), default="", blank=True, max_length=255)

    def __unicode__(self):
        if self.choices:
            return '%s (%s)' % (self.question_label, ', '.join(self.choices))
        return self.question_label

    class Meta:
        verbose_name = _("extra question")
        verbose_name_plural = _("extra questions")

    @property
    def reduction_dict(self):
        if not self.price_reduction:
            return {}
        return dict(zip(self.choices, self.price_reduction))


"""
from StringIO import StringIO
from activities.models import Course

c=Course.objects.all()[0]
s=StringIO()

c.get_js_csv(s)
s.getvalue()

f = open('/Users/grfavre/Desktop/excel-sucks.csv', 'w')
c.get_js_csv(f)
f.close()

"""
