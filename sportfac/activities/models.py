from django.db import models
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
SCHOOL_YEARS = (
    (1, _("1")),
    (2, _("2")),
    (3, _("3")),
    (4, _("4")),
    (5, _("5")),
    (6, _("6")),
)


class Activity(models.Model):
    """
    An activity
    """
    name = models.CharField(max_length=50, db_index=True, unique=True)
    slug = models.SlugField(max_length=50, db_index=True, unique=True)
    image = models.ImageField(upload_to='/activities', null=True, blank=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = _("activity")
        verbose_name_plural = _("activities")
    
    def __unicode__(self):
        return self.name
           
      
class Course(models.Model):
    "A course, i.e. an instance of an activity"
    activity = models.ForeignKey('Activity')
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
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=14, blank=True)
    email = models.EmailField(blank=True)
    
    def __unicode__(self):
        return self.name


class TimeStampedModel(models.Model):
      """
      An abstract base class model that provides self-
.
updating ``created`` and ``modified`` fields.
      """
      created = models.DateTimeField(auto_now_add=True)
      modified = models.DateTimeField(auto_now=True)
      class Meta:
          abstract = True
          