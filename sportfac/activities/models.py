from django.db import models
from django.core.urlresolvers import reverse

from django.utils.translation import ugettext as _

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
)

class Activity(models.Model):
    """
    An activity
    """
    name = models.CharField(max_length=50, db_index=True, unique=True)
    slug = models.SlugField(max_length=50, db_index=True, unique=True)
    image = models.ImageField(upload_to='/activities', null=True, blank=True)
    
    def get_absolute_url(self):
        return reverse('activity-detail', kwargs={"slug": self.slug})

    def __unicode__(self):
        return self.name
    
    class Meta:
        ordering = ['name']
        verbose_name = _("activity")
        verbose_name_plural = _("activities")

    
    
           
      
class Course(models.Model):
    "A course, i.e. an instance of an activity"
    activity = models.ForeignKey('Activity', related_name='courses')
    responsible = models.ForeignKey('Responsible')
    price = models.DecimalField(max_digits=5, decimal_places=2)
    number_of_sessions = models.PositiveSmallIntegerField()
    day = models.PositiveSmallIntegerField(choices=DAYS_OF_WEEK, )
    start_date = models.DateField()
    end_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    place = models.TextField()
    min_participants = models.PositiveSmallIntegerField()
    max_participants = models.PositiveSmallIntegerField()
    schoolyear_min = models.PositiveIntegerField(choices=SCHOOL_YEARS, default="1")
    schoolyear_max = models.PositiveIntegerField(choices=SCHOOL_YEARS, default="6")
    
    
    @property
    def duration(self):
        return self.end_time - self.start_time
    
    @property
    def trimester(self):
        delta = end_date - start_date
        return delta.months % 3
        
    def __unicode__(self):
        return '%s: %s-%s on %s (%s-%s)' % (self.activity.name, 
                                            self.start_date, self.end_date, self.day, 
                                            self.schoolyear_min, self.schoolyear_max)
    
    class Meta:
        ordering = ['start_date', 'activity', 'day']
        verbose_name = _("activity")
        verbose_name_plural = _("activities")
    

class Responsible(models.Model):
    "person repsosible of a course"
    first = models.CharField(max_length=100, blank=True)
    last = models.CharField(max_length=100)
    phone = models.CharField(max_length=14, blank=True)
    email = models.EmailField(blank=True)
    
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