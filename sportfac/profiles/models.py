# -*- coding: utf-8 -*-

from datetime import datetime, date

from django.db import models
from django.template.defaultfilters import slugify
from django.contrib.auth.models import AbstractUser, Group
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.db.models import Sum

from model_utils import Choices
from model_utils.models import StatusModel

from activities.models import SCHOOL_YEARS
from backend import MANAGERS_GROUP, RESPONSIBLE_GROUP
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

class ResponsibleFamilyUserManager(BaseUserManager):
    def get_queryset(self):
        return super(ResponsibleFamilyUserManager, self).get_queryset().filter(groups__name=RESPONSIBLE_GROUP)

class ManagerFamilyUserManager(BaseUserManager):
    def get_queryset(self):
        return super(ManagerFamilyUserManager, self).get_queryset().filter(groups__name=MANAGERS_GROUP)
    

class FamilyUser(PermissionsMixin, AbstractBaseUser):
    COUNTRY = Choices(('CH', _("Switzerland")),
                       ('FL', _("Liechtenstein")),
                       ('D', _("Germany")),
                       ('F', _("France")),
                       ('I', _("Italy")),
                       ('A', _("Austria")))
    email = models.EmailField(verbose_name = _('Email address'), max_length=255, unique=True, db_index=True)
    first_name = models.CharField(_('First name'), max_length=30, blank=True)
    last_name = models.CharField(_('Last name'), max_length=30, blank=True)
    
    address = models.TextField(_("Street"), blank = True)
    zipcode = models.CharField(_("NPA"), blank=True, max_length=5)
    city = models.CharField(_('City'), max_length=100, blank=True)
    country = models.CharField(_('Country'), max_length = 2, choices=COUNTRY, default=COUNTRY.CH)
    private_phone = models.CharField(_("Home phone"), max_length=30, blank=True)
    private_phone2 = models.CharField(_("Mobile phone"), max_length=30, blank=True)
    private_phone3 = models.CharField(_("Other phone"), max_length=30, blank=True)
    
    
    is_active = models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.')
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField('staff status', default=False, help_text=_('Designates whether the user can log into this admin site.'))
    
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    
    finished_registration = models.BooleanField(default=False, verbose_name=_("Finished registration"), help_text=_("For current year"))
    paid = models.BooleanField(default=False, verbose_name=_("Has paid"), help_text=_("For current year"))
    
    billing_identifier = models.CharField(_('Billing identifier'), max_length=45, blank=True)
    total = models.PositiveIntegerField(default=0, verbose_name=_("Total to be paid"))
    
    
    __original_status = None
    
    objects = FamilyManager()
    responsible_objects = ResponsibleFamilyUserManager()
    managers_objects = ManagerFamilyUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('first_name', 'last_name', 'zipcode', 'city', 'country')
    
    class Meta:
        get_latest_by = "date_joined"
        ordering =('last_name', 'first_name')
    
    def __init__(self, *args, **kwargs):
        super(FamilyUser, self).__init__(*args, **kwargs)
        self.__original_status = self.finished_registration
    
    def get_full_name(self):
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()
    
    @property
    def best_phone(self):
        return self.private_phone2 or self.private_phone1 or self.private_phone3
    
    @property
    def full_name(self):
        return self.get_full_name()
    
    def get_short_name(self):
        return self.first_name
    
    @property
    def children_names(self):
        return ', '.join([unicode(child) for child in self.children.all()])
    
    def get_registrations(self, validated=True):
        return Registration.valid.filter(child__in=self.children.all())
    
    def update_total(self):
        registrations = self.get_registrations(True)
        total = registrations.aggregate(Sum('course__price')).get('course__price__sum')
        self.total = total or 0
    
    def update_billing_identifier(self):
        if self.pk:
            self.billing_identifier = slugify('%s-%i' % (self.last_name, self.id))
    
    def get_absolute_url(self):
        return reverse('profiles_account')
    
    def get_manager(self):
        from backend import MANAGERS_GROUP
        if self.is_superuser or self.is_admin:
            return True
        return MANAGERS_GROUP in self.groups.values_list("name", flat=True)
    
    def set_manager(self, value):
        from backend import MANAGERS_GROUP
        managers = Group.objects.get(name=MANAGERS_GROUP)
        if value:
            managers.user_set.add(self)
        else:
            managers.user_set.remove(self)
    
    is_manager = property(get_manager, set_manager)
    
    def get_responsible_status(self):
        from backend import RESPONSIBLE_GROUP
        if self.is_superuser or self.is_admin:
            return True
        return RESPONSIBLE_GROUP in self.groups.values_list("name", flat=True)
    
    def set_responsible_status(self, value):
        from backend import RESPONSIBLE_GROUP
        managers = Group.objects.get(name=RESPONSIBLE_GROUP)
        if value:
            managers.user_set.add(self)
        else:
            managers.user_set.remove(self)

    is_responsible = property(get_responsible_status, set_responsible_status)
    
    def is_responsible_of(self, course):
        return course in self.courses.all()
            
      
    def has_module_perms(self, app_label):
        staff_apps = ['activities', 'profiles', 'constance', 'extended_flatpages']
        # no registration nore auth
        if self.is_superuser:
            return True
        if self.is_staff and app_label in staff_apps:
            return True
        return False
            
    def get_update_url(self):
        return reverse('backend:user-update', kwargs={'pk': self.pk})
    
    def get_delete_url(self):
        return reverse('backend:user-delete', kwargs={'pk': self.pk})

    def get_payment_url(self):
        return reverse('backend:user-pay', kwargs={'pk': self.pk})

    
    def get_backend_url(self):
        return reverse('backend:user-detail', kwargs={'pk': self.pk})
    
    def get_from_address(self):
        return "%s %s <%s>" % (self.first_name, self.last_name, self.email)
        
    
    def __unicode__(self):
        return self.get_from_address()
    
    
    def save(self, *args, **kwargs):
        if self.finished_registration != self.__original_status:
            for registration in self.get_registrations(self.__original_status):
                registration.validated=self.finished_registration
                registration.save()
        self.update_total()
        self.update_billing_identifier()
        super(FamilyUser, self).save(*args, **kwargs)
    
    

# Create your models here.
class Child(TimeStampedModel):
    SEX = Choices(('M', _('Male'))  , 
                  ('F', _('Female')) )
    NATIONALITY = Choices(('CH', _('Swiss'))  , 
                          ('FL', _('Liechtenstein')),
                          ('DIV', _('Other')) )
    LANGUAGE = Choices(('D', 'Deutsch')  , 
                       ('E', 'English'),
                       ('F', u'Français'),
                       ('I', 'Italiano') )

    first_name = models.CharField(_("First name"), max_length=50)
    last_name = models.CharField(_("Last name"), max_length=50)
    sex = models.CharField(_("Sex"), max_length=1, choices=SEX)
    birth_date = models.DateField(_("Birth date"))
    nationality = models.CharField(choices=NATIONALITY, max_length=3, default=NATIONALITY.CH)
    language = models.CharField(choices=LANGUAGE, max_length=2, default=LANGUAGE.F)
    
    school_year = models.ForeignKey('SchoolYear')
    teacher = models.ForeignKey('Teacher', related_name="students", null=True, on_delete=models.SET_NULL)
    
    
    family = models.ForeignKey('FamilyUser', related_name='children')
    courses = models.ManyToManyField('activities.Course', through="Registration")
        
    
    class Meta:
        ordering = ('last_name', 'first_name',)
        abstract = False
    
    def get_update_url(self):
        return reverse('backend:child-update', kwargs={'pk': self.pk, 'user': self.family.pk})
    
    def get_delete_url(self):
        return reverse('backend:child-delete', kwargs={'pk': self.pk, 'user': self.family.pk})
    
    def get_backend_url(self):
        return reverse('backend:user-detail', kwargs={'pk': self.family.pk})
    
    def get_full_name(self):
        full_name = '%s %s' % (self.first_name.title(), self.last_name.title())
        return full_name.strip()
    
    @property
    def full_name(self):
        return self.get_full_name()

    @property
    def js_sex(self):
        if self.sex == self.SEX.M:
            return '1'
        return '2'
    
    @property
    def js_birth_date(self):
        return self.birth_date.strftime('%d.%m.%Y')
    
    def __unicode__(self):
        return self.get_full_name()

class RegistrationManager(models.Manager):
    def get_queryset(self):
        return super(RegistrationManager, self).get_queryset().exclude(status=Registration.STATUS.canceled)
    
    def all_with_deleted(self):
        return super(RegistrationManager, self).get_queryset().all()
    
    def waiting(self):
        return self.get_queryset().filter(status=Registration.STATUS.waiting)
    
    def validated(self):
        return self.get_queryset().filter(status=Registration.STATUS.valid)

    

class Registration(TimeStampedModel, StatusModel):
    STATUS = Choices(('waiting', _("Waiting parent's confirmation")),
                     ('valid', _("Validated by parent")),
                     ('canceled', _("Canceled by administrator")),
                     ('confirmed', _("Confirmed by administrator")),
                     )
    course = models.ForeignKey('activities.Course', related_name="participants", verbose_name=_("Course"))
    child = models.ForeignKey('Child', related_name="registrations")
    
    objects = RegistrationManager()
    
    @property
    def extra_needs(self):
        return self.course.activity.extra.all().exclude(id__in=self.extra_infos.values_list('key'))  
    
    def is_valid(self):
        return self.extra_needs.count() == 0
            
    def __unicode__(self):
        return _(u'%(child)s ⇒ course %(number)s (%(activity)s)') % {'child': unicode(self.child), 
                                                                      'number': self.course.number,
                                                                      'activity': self.course.activity.name}
 
    def set_waiting(self):
        self.status = self.STATUS.waiting
  
    def set_valid(self):
        self.status = self.STATUS.valid
    
    def set_confirmed(self):
        self.status = self.STATUS.confirmed
    
    def cancel(self):
        self.status = self.STATUS.canceled 
    
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
    
    def get_delete_url(self):
        return reverse('backend:registration-delete', kwargs={'pk': self.pk})

    def get_update_url(self):
        return reverse('backend:registration-update', kwargs={'pk': self.pk})

    
    class Meta:
        unique_together = ('course', 'child')
        verbose_name = _("Registration")
        verbose_name_plural = _("Registrations")
        ordering = ('child__last_name', 'child__first_name', 'course__start_date')

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
        ordering = ('year',)
    

class Teacher(models.Model):
    number = models.IntegerField(db_index=True, unique=True, null=True, blank=True, verbose_name=_("Number"))

    first_name = models.CharField(_("First name"), max_length=50)
    last_name = models.CharField(_("Last name"), max_length=50, db_index=True)
    years = models.ManyToManyField('SchoolYear', verbose_name=_("School years"))
    
    def __unicode__(self):
        years = ' - '.join([unicode(year) for year in self.years.all()])
        return '%s %s (%s)' % (self.first_name, self.last_name, years)

    def get_full_name(self):
        return '%s %s ' % (self.first_name, self.last_name)
            
    def get_update_url(self):
        return reverse('backend:teacher-update', kwargs={'pk': self.pk})
    
    def get_delete_url(self):
        return reverse('backend:teacher-delete', kwargs={'pk': self.pk})
    
    def get_backend_url(self):
        return reverse('backend:teacher-detail', kwargs={'pk': self.pk})

    @property
    def years_label(self):
        return ', '.join([str(year) for year in self.years.all()])
    
    class Meta:
        ordering = ('last_name', 'first_name')
        verbose_name = _("teacher")
        verbose_name_plural = _("teachers")

        
        
        
