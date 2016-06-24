# -*- coding: utf-8 -*-
from datetime import datetime, date

from django.db import models
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy
from django.utils.translation import ugettext as _

from ckeditor.fields import RichTextField
from autoslug import AutoSlugField

from sportfac.models import TimeStampedModel
from .utils import course_to_js_csv


DAYS_OF_WEEK = (
    (1, ugettext_lazy('Monday')),
    (2, ugettext_lazy('Tuesday')),
    (3, ugettext_lazy('Wednesday')),
    (4, ugettext_lazy('Thursday')),
    (5, ugettext_lazy('Friday')),
    (6, ugettext_lazy('Saturday')),
    (7, ugettext_lazy('Sunday')),
)

SCHOOL_YEARS = (
    (1, ugettext_lazy("1st HARMOS")),
    (2, ugettext_lazy("2nd HARMOS")),
    (3, ugettext_lazy("3rd HARMOS")),
    (4, ugettext_lazy("4th HARMOS")),
    (5, ugettext_lazy("5th HARMOS")),
    (6, ugettext_lazy("6th HARMOS")),
    (7, ugettext_lazy("7th HARMOS")),
    (8, ugettext_lazy("8th HARMOS")),
    (9, ugettext_lazy("9th HARMOS")),
    (10, ugettext_lazy("10th HARMOS")),
    (11, ugettext_lazy("11th HARMOS")),
    (12, ugettext_lazy("12th HARMOS")),
)

class Activity(TimeStampedModel):
    """
    An activity
    """
    name = models.CharField(max_length=50, db_index=True, unique=True, verbose_name=ugettext_lazy("Name"))
    number = models.CharField(max_length=30,
                              db_index=True, unique=True, 
                              null=True, blank=True, 
                              verbose_name=ugettext_lazy("Identifier"))
    slug = AutoSlugField(populate_from='name', max_length=50, db_index=True, unique=True, 
                         help_text=ugettext_lazy("Part of the url. Cannot contain punctuation, spaces or accentuated letters"))
    informations = RichTextField(verbose_name=_("Informations"), blank=True, 
                                 help_text=ugettext_lazy("Specific informations like outfit."))
    description = RichTextField(verbose_name=_("Description"), blank=True)
    
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
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        ordering = ['name']
        verbose_name = _("activity")
        verbose_name_plural = _("activities")


           

class ExtraNeed(TimeStampedModel):
    activity = models.ForeignKey('Activity', related_name='extra')
    question_label = models.CharField(max_length=255, verbose_name=ugettext_lazy("Question"), 
                                      help_text=ugettext_lazy("e.g. Shoes size?"))
    
    def __unicode__(self):
        return self.question_label


class Course(TimeStampedModel):
    "A course, i.e. an instance of an activity"
    activity = models.ForeignKey('Activity', related_name='courses', 
                                 verbose_name=ugettext_lazy("Activity"))
    number = models.CharField(max_length=30,
                              db_index=True, unique=True, 
                              null=True, blank=True, 
                              verbose_name=ugettext_lazy("Identifier"))
    uptodate = models.BooleanField(verbose_name=ugettext_lazy("Course up to date"), default=True)
    responsible = models.ForeignKey('profiles.FamilyUser', verbose_name=ugettext_lazy("Responsible"), related_name='courses')

    price = models.DecimalField(max_digits=5, decimal_places=2, 
                                verbose_name=ugettext_lazy("Price"), 
                                null=True, 
                                blank=True)
    number_of_sessions = models.PositiveSmallIntegerField(verbose_name=ugettext_lazy("Number of sessions"))
    day = models.PositiveSmallIntegerField(choices=DAYS_OF_WEEK, verbose_name=ugettext_lazy("Day"), default=1)
    start_date = models.DateField(verbose_name=ugettext_lazy("Start date"))
    end_date = models.DateField(verbose_name=ugettext_lazy("End date"))
    start_time = models.TimeField(verbose_name=ugettext_lazy("Start time"))
    end_time = models.TimeField(verbose_name=ugettext_lazy("End time"))
    place = models.TextField(verbose_name=ugettext_lazy("Place"))
    min_participants = models.PositiveSmallIntegerField(verbose_name=ugettext_lazy("Minimal number of participants"))
    max_participants = models.PositiveSmallIntegerField(verbose_name=ugettext_lazy("Maximal number of participants"))
    schoolyear_min = models.PositiveIntegerField(choices=SCHOOL_YEARS, default="1", verbose_name=ugettext_lazy("Minimal school year"))
    schoolyear_max = models.PositiveIntegerField(choices=SCHOOL_YEARS, default="8", verbose_name=ugettext_lazy("Maximal school year"))
    
    
    @property
    def day_name(self):
        return unicode(dict(DAYS_OF_WEEK).get(self.day, str(self.day)))
    
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
        return base
    
    def detailed_label(self):
        base = unicode(self)
        if self.full:
            fullness = _('Course full')
        else:
            fullness = _('%(available)s out of %(total)s places remaining') 
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

    def get_custom_mail_responsible_url(self):
        return reverse('activities:mail-participants-custom', kwargs={'course': self.pk})

    def get_mail_responsible_url(self):
        return reverse('backend:course-mail-responsible', kwargs={'course': self.pk})
    
    def get_mail_infos_url(self):
        return reverse('activities:mail-responsible', kwargs={'course': self.pk})
    
    def get_mail_confirmation_url(self):
        return reverse('backend:course-mail-confirmation', kwargs={'course': self.pk})
    
    def get_absences_url(self):
        return reverse('activities:course-absence', kwargs={'course': self.pk})

    def get_backend_absences_url(self):
        return reverse('backend:course-absence', kwargs={'course': self.pk})

    
    def get_js_export_url(self):
        return reverse('backend:course-js-export', kwargs={'course': self.pk})
    
    def get_js_csv(self, filelike):
        course_to_js_csv(self, filelike)
    
    @property
    def get_js_name(self):
        return '%s - %s' % (self.number, self.responsible.full_name)
    
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