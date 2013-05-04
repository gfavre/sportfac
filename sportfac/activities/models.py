from django.db import models
from django.utils.translation import ugettext as _

DAYS_OF_WEEK = (
    (0, _('Monday')),
    (1, _('Tuesday')),
    (2, _('Wednesday')),
    (3, _('Thursday')),
    (4, _('Friday')),
    (5, _('Saturday')),
    (6, _('Sunday')),
)

class Activity(models.Model):
    """
    An activity
    """
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50)
    image = models.ImageField(upload_to='/activities')    
      
class Course(models.Model):
    "A course, i.e. an instance of an activity"
    activity = models.ForeignKey('Activity')
    responsible = models.ForeignKey('Responsible')
    price = models.DecimalField(max_digits=5, decimal_places=2)
    number_of_sessions = models.PositiveSmallIntegerField()
    day = models.CharField(max_length=1, choices=DAYS_OF_WEEK)
    start_date = models.DateField()
    end_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    place = models.CharField(max_length=200)
    min_participants = models.PositiveSmallIntegerField()
    max_participants = models.PositiveSmallIntegerField()
    schoolyear_min = models.PositiveIntegerField()
    schoolyear_max = models.PositiveIntegerField()
    

    
    @property
    def duration(self):
        return self.end_time - self.start_time
    
    @property
    def trimester(self):
        delta = end_date - start_date
        return delta.months % 3
    

class Responsible(models.Model):
    "person repsosible of a course"
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=14)


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
          