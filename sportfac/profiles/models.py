from django.db import models
from django.utils.translation import gettext as _
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.utils import timezone

from activities.models import SCHOOL_YEARS


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
      
      def create_superuser(self, email, first_name, last_name, zipcode, city, country, password, **extra_fields):
          """
          Creates and saves a superuser with the given email, favorite topping and password.
          """
          user = self.create_user(email, first_name, last_name, zipcode, city, country, password, **extra_fields)
          user.is_admin = True
          user.is_staff = True
          user.is_superuser = True
          user.save(using=self._db)
          return user


class FamilyUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(verbose_name = 'email address', max_length=255, unique=True, db_index=True)
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=30, blank=True)
    
    address = models.TextField(_("Street"), blank = True)
    zipcode = models.PositiveIntegerField(_("NPA"))
    city = models.CharField(_('City'), max_length=100)
    country = models.CharField(_('Country'), max_length = 100, default=_("Switzerland"))
    private_phone = models.CharField(max_length=12, blank=True)
    private_phone2 = models.CharField(max_length=12, blank=True)
    
    is_active = models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.')
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField('staff status', default=False, help_text='Designates whether the user can log into this admin site.')
    
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    
    
    objects = FamilyManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('first_name', 'last_name', 'zipcode', 'city', 'country')
    
    def get_full_name(self):
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()
    
    def get_short_name(self):
        return self.first_name
    
    @property
    def children_names(self):
        return ', '.join([unicode(child) for child in self.children.all()])
    
    def get_absolute_url(self):
        return 'toto'
    
    def __unicode__(self):
        return self.email
    
    

# Create your models here.
class Child(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    sex = models.CharField(max_length=1, choices=(('M', _('Male')), ('F', _('Female'))))
    birth_date = models.DateField()
    school_year = models.ForeignKey('SchoolYear')
    teacher = models.ForeignKey('Teacher')
    
    family = models.ForeignKey('FamilyUser', related_name='children')
    
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    
    
    class Meta:
        ordering = ('first_name',)
        abstract = False
    
    
    def __unicode__(self):
        return '%s %s' % (self.first_name, self.last_name)
    

class SchoolYear(models.Model):
    year = models.PositiveIntegerField(choices=SCHOOL_YEARS, unique=True)
    
    def __unicode__(self):
        try:
            return dict(SCHOOL_YEARS)[self.year]
        except KeyError:
            return unicode(year)
    

class Teacher(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50, db_index=True)
    years = models.ManyToManyField('SchoolYear')
    
    def __unicode__(self):
        years = ' - '.join([unicode(year) for year in self.years.all()])
        return '%s %s (%s)' % (self.first_name, self.last_name, years)
    
    class Meta:
        ordering = ('last_name', 'first_name')
