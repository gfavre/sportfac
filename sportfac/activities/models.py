# -*- coding: utf-8 -*-
from datetime import datetime, date

from django.db import models
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from ckeditor.fields import RichTextField

from sportfac.models import TimeStampedModel

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
    (1, _("1st HARMOS")),
    (2, _("2nd HARMOS")),
    (3, _("3rd HARMOS")),
    (4, _("4th HARMOS")),
    (5, _("5th HARMOS")),
    (6, _("6th HARMOS")),
    (7, _("7th HARMOS")),
    (8, _("8th HARMOS")),
)

class Activity(models.Model):
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
        return reverse('activity-detail', kwargs={"slug": self.slug})

    def __unicode__(self):
        return self.name
    
    
    class Meta:
        ordering = ['name']
        verbose_name = _("activity")
        verbose_name_plural = _("activities")
           

class ExtraNeed(models.Model):
    activity = models.ForeignKey('Activity', related_name='extra')
    question_label = models.CharField(max_length=255, verbose_name=_("Question"), help_text=_("e.g. Shoes size?"))
    
    def __unicode__(self):
        return self.question_label

class Course(models.Model):
    "A course, i.e. an instance of an activity"
    activity = models.ForeignKey('Activity', related_name='courses')
    number = models.IntegerField(db_index=True, unique=True, null=True, blank=True, verbose_name=_("Number"))
    uptodate = models.BooleanField(verbose_name=_("Course up to date"), default=False)
    responsible = models.ForeignKey('Responsible', verbose_name=_("Responsible"))
    price = models.DecimalField(max_digits=5, decimal_places=2, verbose_name=_("Price"))
    number_of_sessions = models.PositiveSmallIntegerField(verbose_name=_("Number of sessions"))
    day = models.PositiveSmallIntegerField(choices=DAYS_OF_WEEK, verbose_name=_("Day"))
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
    


    def __unicode__(self):
        return u'%s (%s): du %s au %s les %s à %s (%sp-%sp)' % (self.activity.name, self.number,
                                                          self.start_date.strftime("%d/%m/%Y"), 
                                                          self.end_date.strftime("%d/%m/%Y"),
                                                          self.day_name.lower(),
                                                          self.start_time.strftime("%H:%M"),
                                                          self.schoolyear_min, self.schoolyear_max)
    
    class Meta:
        ordering = ['start_date', 'activity', 'day']
        verbose_name = _("course")
        verbose_name_plural = _("courses")
    

class Responsible(models.Model):
    "person repsosible of a course"
    first = models.CharField(max_length=100, blank=True, verbose_name=_("First name"), help_text=_("Leave it empty in case of collaboration name"), db_index=True)
    last = models.CharField(max_length=100, verbose_name=_("Last name"), db_index=True)
    phone = models.CharField(max_length=14, blank=True, verbose_name=_("Phone number"))
    email = models.EmailField(blank=True, verbose_name=_("Email"))
    
    def __unicode__(self):
        if self.first:
            return u'%s %s' % (self.first, self.last)
        else:
            return self.last
    
    @property
    def fullname(self):
        return self.__unicode__
    
    class Meta:
        ordering = ['last', 'first']
        verbose_name = _("responsible")
        verbose_name_plural = _("responsibles")          