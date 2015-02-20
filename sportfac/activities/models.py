# -*- coding: utf-8 -*-
from datetime import datetime, date

from django.db import models
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext

from ckeditor.fields import RichTextField

from sportfac.models import TimeStampedModel
from .utils import course_to_js_csv


DAYS_OF_WEEK = (
    (1, ugettext('Monday')),
    (2, ugettext('Tuesday')),
    (3, ugettext('Wednesday')),
    (4, ugettext('Thursday')),
    (5, ugettext('Friday')),
    (6, ugettext('Saturday')),
    (7, ugettext('Sunday')),
)

SCHOOL_YEARS = (
    (1, ugettext("1st HARMOS")),
    (2, ugettext("2nd HARMOS")),
    (3, ugettext("3rd HARMOS")),
    (4, ugettext("4th HARMOS")),
    (5, ugettext("5th HARMOS")),
    (6, ugettext("6th HARMOS")),
    (7, ugettext("7th HARMOS")),
    (8, ugettext("8th HARMOS")),
    (9, ugettext("9th HARMOS")),
    (10, ugettext("10th HARMOS")),
    (11, ugettext("11th HARMOS")),    
)

class Activity(TimeStampedModel):
    """
    An activity
    """
    name = models.CharField(max_length=50, db_index=True, unique=True, verbose_name=_("Name"))
    number = models.IntegerField(verbose_name=_("Number"), db_index=True, unique=True, null=True, blank=True)
    slug = models.SlugField(max_length=50, db_index=True, unique=True, 
                            help_text=_("Part of the url. Cannot contain punctuation, spaces or accentuated letters"))
    informations = RichTextField(blank=True, help_text=_("Specific informations like outfit."))
    description = RichTextField(blank=True)
    
    
    def get_absolute_url(self):
        return reverse('activities:activity-detail', kwargs={"slug": self.slug})

    def __unicode__(self):
        return self.name
    
    class Meta:
        ordering = ['name']
        verbose_name = _("activity")
        verbose_name_plural = _("activities")
           

class ExtraNeed(TimeStampedModel):
    activity = models.ForeignKey('Activity', related_name='extra')
    question_label = models.CharField(max_length=255, verbose_name=_("Question"), help_text=_("e.g. Shoes size?"))
    
    def __unicode__(self):
        return self.question_label


class Course(TimeStampedModel):
    "A course, i.e. an instance of an activity"
    activity = models.ForeignKey('Activity', related_name='courses', verbose_name=_("Activity"))
    number = models.IntegerField(db_index=True, unique=True, null=True, blank=True, verbose_name=_("Identifier"))
    uptodate = models.BooleanField(verbose_name=_("Course up to date"), default=True)
    responsible = models.ForeignKey('profiles.FamilyUser', verbose_name=_("Responsible"), related_name='courses')

    price = models.DecimalField(max_digits=5, decimal_places=2, verbose_name=_("Price"))
    number_of_sessions = models.PositiveSmallIntegerField(verbose_name=_("Number of sessions"))
    day = models.PositiveSmallIntegerField(choices=DAYS_OF_WEEK, verbose_name=_("Day"), default=1)
    start_date = models.DateField(verbose_name=_("Start date"))
    end_date = models.DateField(verbose_name=_("End date"))
    start_time = models.TimeField(verbose_name=_("Start time"))
    end_time = models.TimeField(verbose_name=_("End time"))
    place = models.TextField(verbose_name=_("Place"))
    min_participants = models.PositiveSmallIntegerField(verbose_name=_("Minimal number of participants"))
    max_participants = models.PositiveSmallIntegerField(verbose_name=_("Maximal number of participants"))
    schoolyear_min = models.PositiveIntegerField(choices=SCHOOL_YEARS, default="1", verbose_name=_("Minimal school year"))
    schoolyear_max = models.PositiveIntegerField(choices=SCHOOL_YEARS, default="8", verbose_name=_("Maximal school year"))
    
    
    @property
    def day_name(self):
        return dict(DAYS_OF_WEEK).get(self.day, str(self.day))
    
    @property
    def duration(self):
        return datetime.combine(date.today(), self.end_time) - datetime.combine(date.today(), self.start_time)
    
    @property
    def available_places(self):
        return self.max_participants - self.participants.count()
    
    @property
    def count_participants(self):
        return self.participants.count()
    
    @property
    def percentage_full(self):
        return int(100 * float(self.count_participants) / float(self.max_participants))
    
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
    def short_name(self):
        return '%s (%s)' % (self.activity.name, self.number)    
    
    def __unicode__(self):
        base = _(u'%(activity)s (%(number)s): from %(start)s to %(end)s, every %(day)s at %(hour)s.')
        base %= {'activity': self.activity.name,
                 'number': self.number,
                 'start': self.start_date.strftime("%d/%m/%Y"), 
                 'end': self.end_date.strftime("%d/%m/%Y"),
                 'day': self.day_name.lower(),
                 'hour': self.start_time.strftime("%H:%M"),
                 }
        if self.full:
            fullness = _('Course full')
        else:
            fullness = _('%(available)s out of %(total)s places remaining') 
            fullness %= {'available': self.available_places, 'total': self.max_participants}
        return base + ' ' + fullness
        
    def get_update_url(self):
        return reverse('backend:course-update', kwargs={'course': self.number})
    
    def get_delete_url(self):
        return reverse('backend:course-delete', kwargs={'course': self.number})
    
    def get_backend_url(self):
        return reverse('backend:course-detail', kwargs={'course': self.number})
    
    def get_custom_mail_url(self):
        return reverse('backend:mail-participants-custom', kwargs={'course': self.number})

    def get_custom_mail_responsible_url(self):
        return reverse('activities:mail-participants-custom', kwargs={'course': self.number})

    def get_mail_responsible_url(self):
        return reverse('backend:course-mail-responsible', kwargs={'course': self.number})
    
    def get_js_export_url(self):
        return reverse('backend:course-js-export', kwargs={'course': self.number})
    
    def get_js_csv(self, filelike):
        course_to_js_csv(self, filelike)
    
    @property
    def get_js_name(self):
        return '%s - %s' % (self.number, self.responsible.full_name)
    
    def get_absolute_url(self):
        return reverse('activities:course-detail', kwargs={"course": self.number})


    def save(self, *args, **kwargs):
        super(Course, self).save(*args, **kwargs)
        self.responsible.is_responsible = True

        
    class Meta:
        ordering = ('activity__name', 'number', )
        verbose_name = _("course")
        verbose_name_plural = _("courses")
    
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