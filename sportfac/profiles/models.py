from datetime import datetime, date

from django.db import models
from django.template.defaultfilters import slugify
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.utils import timezone


from activities.models import SCHOOL_YEARS
from sportfac.models import TimeStampedModel


class FamilyManager(BaseUserManager):
      def create_user(self, email, first_name, last_name, zipcode, city, password=None, **extra_fields):
          """
          Creates and saves a User with the given email, favorite topping, and password.
          """
          if not email:
              msg = "Users must have an email address"
              raise ValueError(msg)
          if not first_name:
              msg = "Users must have a first name"
              raise ValueError(msg)
          if not last_name:
              msg = "Users must have a first name"
              raise ValueError(msg)
          if not zipcode:
              msg = "Users must have a zip"
              raise ValueError(msg)
          if not city:
              msg = "Users must have a city"
              raise ValueError(msg)
          
          user = self.model(
              email=FamilyManager.normalize_email(email),
              first_name=first_name,
              last_name=last_name,
              zipcode=zipcode,
              city=city,
              **extra_fields
          )
          user.set_password(password)
          user.save(using=self._db)
          return user
      
      def create_superuser(self, email, first_name, last_name, zipcode, city, password, **extra_fields):
          """
          Creates and saves a superuser with the given email, favorite topping and password.
          """
          user = self.create_user(email=email, first_name=first_name, last_name=last_name,
                                  zipcode=zipcode, city=city, password=password, **extra_fields)
          user.is_admin = True
          user.is_staff = True
          user.is_superuser = True
          user.save(using=self._db)
          return user


class FamilyUser(PermissionsMixin, AbstractBaseUser):
    email = models.EmailField(verbose_name = _('Email address'), max_length=255, unique=True, db_index=True)
    first_name = models.CharField(_('First name'), max_length=30, blank=True)
    last_name = models.CharField(_('Last name'), max_length=30, blank=True)
    
    address = models.TextField(_("Street"), blank = True)
    zipcode = models.PositiveIntegerField(_("NPA"))
    city = models.CharField(_('City'), max_length=100)
    country = models.CharField(_('Country'), max_length = 100, default=_("Switzerland"))
    private_phone = models.CharField(max_length=30, blank=True)
    private_phone2 = models.CharField(max_length=30, blank=True)
    private_phone3 = models.CharField(max_length=30, blank=True)
    
    
    is_active = models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.')
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField('staff status', default=False, help_text=_('Designates whether the user can log into this admin site.'))
    
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    
    finished_registration = models.BooleanField(default=False, verbose_name=_("Finished registration"), help_text=_("For current year"))
    paid = models.BooleanField(default=False, verbose_name=_("Has paid"), help_text=_("For current year"))
    
    
    objects = FamilyManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('first_name', 'last_name', 'zipcode', 'city', 'country')
    
    @property
    def billing_identifier(self):
        return slugify('%s-%i' % (self.last_name, self.id))
    
    def get_full_name(self):
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()
    
    def get_short_name(self):
        return self.first_name
    
    @property
    def children_names(self):
        return ', '.join([unicode(child) for child in self.children.all()])
    
    def get_absolute_url(self):
        return reverse('profiles_account')
    
    
    def has_perm(self, perm, obj=None):
        return True
    
    
    def has_module_perms(self, app_label):
        staff_apps = ['activities', 'profiles', 'constance', 'extended_flatpages']
        # no registration nore auth
        if self.is_superuser:
            return True
        if self.is_staff and app_label in staff_apps:
            return True
        return False
            
    
    def __unicode__(self):
        return self.email
    
    

# Create your models here.
class Child(TimeStampedModel):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    sex = models.CharField(max_length=1, choices=(('M', _('Male')), ('F', _('Female'))))
    birth_date = models.DateField()
    school_year = models.ForeignKey('SchoolYear')
    teacher = models.ForeignKey('Teacher', related_name="students", null=True, on_delete=models.SET_NULL)
    
    family = models.ForeignKey('FamilyUser', related_name='children')
    courses = models.ManyToManyField('activities.Course', through="Registration")
        
    
    class Meta:
        ordering = ('first_name',)
        abstract = False
    
    
    def __unicode__(self):
        return '%s %s' % (self.first_name, self.last_name)


class Registration(TimeStampedModel):
    course = models.ForeignKey('activities.Course', related_name="participants")
    child = models.ForeignKey('Child')
    validated = models.BooleanField(default=False, db_index=True)
    paid = models.BooleanField(default=False, db_index=True)
    
    @property
    def extra_needs(self):
        return self.course.activity.extra.all().exclude(id__in=self.extra_infos.values_list('key'))  
    
    def is_valid(self):
        return self.extra_needs.count() == 0
            
    def __unicode__(self):
        return '%s -> course %s' % (unicode(self.child), self.course.number)
    
    def overlap(self, r2):
        "Test if another registration object overlaps with this one."  
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
        elif interval.seconds < (60*30):
            # less than half an hour between courses
            return True
        return False   
    
    class Meta:
        unique_together = ('course', 'child')
        verbose_name = _("Registration")
        verbose_name_plural = _("Registrations")
        ordering = ('child__first_name', 'course__start_date')

class ExtraInfo(models.Model):
    registration = models.ForeignKey('Registration', related_name='extra_infos')
    key =  models.ForeignKey('activities.ExtraNeed')
    value = models.CharField(max_length=255)


class SchoolYear(models.Model):
    year = models.PositiveIntegerField(_("School year"), choices=SCHOOL_YEARS, unique=True)
    
    def __unicode__(self):
        try:
            return dict(SCHOOL_YEARS)[self.year]
        except KeyError:
            return unicode(year)
    
    class Meta:
        verbose_name = _("School year")
        verbose_name_plural = _("School years")
    

class Teacher(models.Model):
    number = models.IntegerField(db_index=True, unique=True, null=True, blank=True, verbose_name=_("Number"))

    first_name = models.CharField(_("First name"), max_length=50)
    last_name = models.CharField(_("Last name"), max_length=50, db_index=True)
    years = models.ManyToManyField('SchoolYear', verbose_name=_("School years"))
    
    def __unicode__(self):
        years = ' - '.join([unicode(year) for year in self.years.all()])
        return '%s %s (%s)' % (self.first_name, self.last_name, years)
    
    @property
    def years_label(self):
        return ', '.join([str(year) for year in self.years.all()])
    
    class Meta:
        ordering = ('last_name', 'first_name')
        verbose_name = _("teacher")
        verbose_name_plural = _("teachers")

        
        
        
