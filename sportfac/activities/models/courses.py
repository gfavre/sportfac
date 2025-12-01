from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta

from ckeditor_uploader.fields import RichTextUploadingField
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import models
from django.template.defaultfilters import date as _date
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from model_utils import Choices

from sportfac.models import TimeStampedModel

from ..utils import course_to_js_csv


DAYS_OF_WEEK = (
    (1, _("Monday")),
    (2, _("Tuesday")),
    (3, _("Wednesday")),
    (4, _("Thursday")),
    (5, _("Friday")),
    (6, _("Saturday")),
    (7, _("Sunday")),
)

SCHOOL_YEARS = settings.KEPCHUP_YEAR_NAMES.items()

AGES = Choices(*[(age, f"a{age}", _("%i years old") % age) for age in settings.KEPCHUP_AGES])


class CourseManager(models.Manager):
    def visible(self):
        return self.get_queryset().filter(visible=True)

    def registerable(self):
        return self.get_queryset().exclude(course_type=Course.TYPE.unregistered_course).filter(visible=True)

    def camps(self):
        return self.get_queryset().filter(type=Course.TYPE.camp)


class Course(TimeStampedModel):
    """A course, i.e. an instance of an activity"""

    TYPE = Choices(
        ("course", _("Course (single day per week)")),
        ("unregistered_course", _("Unregistered course (single day per week)")),
        ("multicourse", _("Course (multiple days per week)")),
        ("camp", _("Camp")),
    )
    activity = models.ForeignKey(
        "Activity", related_name="courses", verbose_name=_("Activity"), on_delete=models.CASCADE
    )
    course_type = models.CharField(_("Course type"), max_length=30, choices=TYPE, default=TYPE.course, db_index=True)
    number = models.CharField(
        max_length=30,
        db_index=True,
        unique=True,
        null=True,
        blank=True,
        verbose_name=_("Identifier"),
    )
    name = models.CharField(null=True, blank=True, max_length=50, verbose_name=_("Displayed name"))
    comments = RichTextUploadingField(verbose_name=_("Comments"), blank=True)

    uptodate = models.BooleanField(verbose_name=_("Course up to date"), default=True)
    visible = models.BooleanField(verbose_name=_("Course visible"), default=True, db_index=True)

    instructors = models.ManyToManyField(
        "profiles.FamilyUser",
        verbose_name=_("Instructors"),
        related_name="course",
        through="CoursesInstructors",
    )

    local_city_override = models.ManyToManyField(to="profiles.City", verbose_name=_("Local city override"), blank=True)
    price = models.DecimalField(max_digits=5, decimal_places=2, verbose_name=_("Price"), null=True, blank=True)
    price_local = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Price for local people"),
    )
    price_family = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Price for family members"),
        help_text=_("Applied for the second and following members registered to the same course"),
    )
    price_local_family = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Price for local family members"),
        help_text=_(
            "Applied for the second and following members registered to the same course if the family is local"
        ),
    )
    price_description = models.TextField(_("Informations about pricing"), blank=True)

    number_of_sessions = models.PositiveSmallIntegerField(verbose_name=_("Number of sessions"), default=0)
    day = models.PositiveSmallIntegerField(choices=DAYS_OF_WEEK, verbose_name=_("Day"), default=1, blank=True)
    start_date = models.DateField(verbose_name=_("Start date"), null=True)
    end_date = models.DateField(verbose_name=_("End date"), null=True)
    start_time = models.TimeField(verbose_name=_("Start time"), null=True, blank=True)
    end_time = models.TimeField(verbose_name=_("End time"), null=True, blank=True)

    start_time_mon = models.TimeField(verbose_name=_("Start time, mondays"), null=True, blank=True)
    end_time_mon = models.TimeField(verbose_name=_("End time, mondays"), null=True, blank=True)
    start_time_tue = models.TimeField(verbose_name=_("Start time, tuesdays"), null=True, blank=True)
    end_time_tue = models.TimeField(verbose_name=_("End time, tuesdays"), null=True, blank=True)
    start_time_wed = models.TimeField(verbose_name=_("Start time, wednesdays"), null=True, blank=True)
    end_time_wed = models.TimeField(verbose_name=_("End time, wednesdays"), null=True, blank=True)
    start_time_thu = models.TimeField(verbose_name=_("Start time, thursdays"), null=True, blank=True)
    end_time_thu = models.TimeField(verbose_name=_("End time, thursdays"), null=True, blank=True)
    start_time_fri = models.TimeField(verbose_name=_("Start time, fridays"), null=True, blank=True)
    end_time_fri = models.TimeField(verbose_name=_("End time, fridays"), null=True, blank=True)
    start_time_sat = models.TimeField(verbose_name=_("Start time, saturdays"), null=True, blank=True)
    end_time_sat = models.TimeField(verbose_name=_("End time, saturdays"), null=True, blank=True)
    start_time_sun = models.TimeField(verbose_name=_("Start time, sundays"), null=True, blank=True)
    end_time_sun = models.TimeField(verbose_name=_("End time, sundays"), null=True, blank=True)

    place = models.TextField(verbose_name=_("Place"))
    min_participants = models.PositiveSmallIntegerField(verbose_name=_("Minimal number of participants"))
    max_participants = models.PositiveSmallIntegerField(verbose_name=_("Maximal number of participants"))
    allow_new_participants = models.BooleanField(
        default=True,
        verbose_name=_("Allow registrations"),
        help_text=_(
            "If unchecked, no new registration will be possible. This is more restrictive than the course being full."
        ),
    )
    places_available_reminder_sent_on = models.DateTimeField(
        verbose_name=_("Places available reminder sent on"), null=True, blank=True
    )

    schoolyear_min = models.PositiveIntegerField(
        choices=SCHOOL_YEARS, verbose_name=_("Minimal school year"), blank=True, null=True
    )
    schoolyear_max = models.PositiveIntegerField(
        choices=SCHOOL_YEARS, verbose_name=_("Maximal school year"), blank=True, null=True
    )

    age_min = models.PositiveIntegerField(
        choices=AGES,
        verbose_name=_("Minimal age"),
        help_text=_("At the beginning of course"),
        blank=True,
        null=True,
    )
    age_max = models.PositiveIntegerField(
        choices=AGES,
        verbose_name=_("Maximal age"),
        help_text=_("At the beginning of course"),
        blank=True,
        null=True,
    )
    min_birth_date = models.DateField(verbose_name=_("Minimal birth date to register"), null=True, editable=False)
    max_birth_date = models.DateField(verbose_name=_("Maximal birth date to register"), null=True, editable=False)

    announced_js = models.BooleanField(_("Course announced to J+S"), default=False)

    # DENORMALIZED FIELDS
    has_waiting_list = models.BooleanField(default=False, editable=False)
    nb_participants = models.SmallIntegerField(verbose_name=_("Current nb of participants"), default=0)

    objects = CourseManager()

    class Meta:
        ordering = (
            "activity__name",
            "number",
        )
        verbose_name = _("course")
        verbose_name_plural = _("courses")

    @property
    def accepts_registrations(self):
        # Admin has manually blocked registrations
        if not self.allow_new_participants:
            return False
        if self.full:
            return False
        if self.has_waiting_list:
            return False
        return True

    @property
    def ages(self):
        return list(
            range(
                self.age_min or settings.KEPCHUP_AGES[0],
                (self.age_max or settings.KEPCHUP_AGES[-1]) + 1,
            )
        )

    @property
    def ages_label(self):
        return [dict(AGES)[age] for age in self.ages]

    @property
    def all_dates(self):
        if settings.KEPCHUP_EXPLICIT_SESSION_DATES:
            sessions = list(self.sessions.all())  # use prefetched
            sessions.sort(key=lambda s: s.date)
            return [session.date for session in sessions]
        return [
            self.start_date + timedelta(days=i)
            for i in range(0, (self.end_date - self.start_date).days + 1, 7)
            if self.start_date + timedelta(days=i) <= self.end_date
        ]

    @property
    def available_places(self):
        return self.max_participants - self.count_participants

    @property
    def backend_absences_url(self):
        return self.get_backend_absences_url()

    @property
    def backend_url(self):
        return self.get_backend_url()

    @property
    def count_participants(self):
        return self.nb_participants

    @property
    def day_name(self):
        days = dict(DAYS_OF_WEEK)
        if self.is_camp:
            if self.start_date and self.end_date:
                return str(days[self.start_date.isoweekday()]) + " - " + str(days[self.end_date.isoweekday()])
            return ""
        return str(dict(DAYS_OF_WEEK).get(self.day, str(self.day)))

    @property
    def days_names(self):
        days = dict(DAYS_OF_WEEK)
        out = []
        if self.start_time_mon:
            out.append(str(days[1]))
        if self.start_time_tue:
            out.append(str(days[2]))
        if self.start_time_wed:
            out.append(str(days[3]))
        if self.start_time_thu:
            out.append(str(days[4]))
        if self.start_time_fri:
            out.append(str(days[5]))
        if self.start_time_sat:
            out.append(str(days[6]))
        if self.start_time_sun:
            out.append(str(days[7]))
        return out

    @property
    def delete_url(self):
        return self.get_delete_url()

    @property
    def duration(self):  # noqa: CCR001
        if self.is_camp:
            if settings.KEPCHUP_EXPLICIT_SESSION_DATES:
                if self.sessions.exists():
                    return self.sessions.last().date + timedelta(days=1) - self.sessions.first().date
                return None
            return (self.end_date - self.start_date) + timedelta(days=1)
        if self.is_multi_course:
            return max(
                [
                    datetime.combine(date.today(), self.end_time_mon or time(0, 0))
                    - datetime.combine(date.today(), self.start_time_mon or time(0, 0)),
                    datetime.combine(date.today(), self.end_time_tue or time(0, 0))
                    - datetime.combine(date.today(), self.start_time_tue or time(0, 0)),
                    datetime.combine(date.today(), self.end_time_wed or time(0, 0))
                    - datetime.combine(date.today(), self.start_time_wed or time(0, 0)),
                    datetime.combine(date.today(), self.end_time_thu or time(0, 0))
                    - datetime.combine(date.today(), self.start_time_thu or time(0, 0)),
                    datetime.combine(date.today(), self.end_time_fri or time(0, 0))
                    - datetime.combine(date.today(), self.start_time_fri or time(0, 0)),
                    datetime.combine(date.today(), self.end_time_sat or time(0, 0))
                    - datetime.combine(date.today(), self.start_time_sat or time(0, 0)),
                    datetime.combine(date.today(), self.end_time_sun or time(0, 0))
                    - datetime.combine(date.today(), self.start_time_sun or time(0, 0)),
                ]
            )
        return datetime.combine(date.today(), self.end_time or time(23, 59)) - datetime.combine(
            date.today(), self.start_time or time(0, 0)
        )

    @property
    def full(self):
        return self.count_participants >= self.max_participants

    @property
    def get_js_name(self):
        return f"{self.number} - {self.activity.name}"

    @property
    def has_issue(self):
        return self.count_participants > self.max_participants

    @property
    def has_participants(self):
        return self.participants.exists()

    @property
    def start_hours(self):
        out = []
        if self.start_time_mon:
            out.append(self.start_time_mon)
        if self.start_time_tue:
            out.append(self.start_time_tue)
        if self.start_time_wed:
            out.append(self.start_time_wed)
        if self.start_time_thu:
            out.append(self.start_time_thu)
        if self.start_time_fri:
            out.append(self.start_time_fri)
        if self.start_time_sat:
            out.append(self.start_time_sat)
        if self.start_time_sun:
            out.append(self.start_time_sun)
        return out

    @property
    def is_course(self):
        return self.course_type == self.TYPE.course

    @property
    def is_camp(self):
        return self.course_type == self.TYPE.camp

    @property
    def is_multi_course(self):
        return self.course_type == self.TYPE.multicourse

    @property
    def is_unregistered_course(self):
        return self.course_type == self.TYPE.unregistered_course

    @property
    def last_convocation_email(self):
        receipt = self.email_receipts.filter(type=TemplatedEmailReceipt.TYPE.convocation).order_by("modified").last()
        if receipt:
            return receipt.modified
        return None

    @property
    def last_instructor_email(self):
        receipt = self.email_receipts.filter(type=TemplatedEmailReceipt.TYPE.instructors).order_by("modified").last()
        if receipt:
            return receipt.modified
        return None

    @property
    def long_name(self):
        if self.name:
            return f"{self.short_name} - {self.name}"
        return self.short_name

    @property
    def minimal_participants_reached(self):
        return self.count_participants >= self.min_participants

    @property
    def percentage_full(self):
        if self.full or not self.allow_new_participants:
            return 100
        try:
            return int(100 * float(self.count_participants) / float(self.max_participants))
        except ZeroDivisionError:
            return 100

    @property
    def school_years(self):
        if self.schoolyear_min and self.schoolyear_max:
            return list(range(self.schoolyear_min, self.schoolyear_max + 1))
        return []

    @property
    def school_years_label(self):
        return [dict(SCHOOL_YEARS)[year] for year in self.school_years]

    @property
    def short_name(self):
        return f"{self.activity.name} ({self.number})"

    @property
    def update_url(self):
        return self.get_update_url()

    def add_session(self, date, instructor=None, update_cache=True):
        from absences.models import Session

        if settings.KEPCHUP_ABSENCES_RELATE_TO_ACTIVITIES:
            session, created = Session.objects.get_or_create(
                course=self,
                date=date,
                defaults={"instructor": instructor, "activity": self.activity},
            )
        else:
            session, created = Session.objects.get_or_create(
                course=self, date=date, defaults={"instructor": instructor}
            )
        session.fill_absences()
        session.update_courses_dates(update_cache=update_cache)
        return session

    def detailed_label(self):
        base = str(self)
        if self.is_course:
            dates = _("from %(start)s to %(end)s, every %(day)s at %(hour)s.")
            return (
                base
                + ", "
                + dates
                % {
                    "start": self.start_date and self.start_date.strftime("%d/%m/%Y"),
                    "end": self.end_date and self.end_date.strftime("%d/%m/%Y"),
                    "day": self.day_name.lower(),
                    "hour": self.start_time.strftime("%H:%M"),
                }
            )
        if self.is_camp:
            return base + ", {}-{}".format(self.start_date.strftime("%d/%m/%Y"), self.end_date.strftime("%d/%m/%Y"))
        return base

    def get_absences_url(self):
        return reverse("activities:course-absence", kwargs={"course": self.pk})

    def get_absolute_url(self):
        return reverse("activities:course-detail", kwargs={"course": self.pk})

    def get_backend_absences_url(self):
        if settings.KEPCHUP_ABSENCES_RELATE_TO_ACTIVITIES:
            return reverse("backend:activity-absences", kwargs={"activity": self.activity.slug}) + f"?c={self.pk}"
        return reverse("backend:course-absence", kwargs={"course": self.pk})

    def get_custom_mail_custom_users_instructors_url(self):
        return reverse("activities:mail-custom-participants-custom", kwargs={"course": self.pk})

    def get_backend_url(self):
        return reverse("backend:course-detail", kwargs={"course": self.pk})

    def get_custom_mail_url(self):
        return reverse("backend:mail-participants-custom", kwargs={"course": self.pk})

    def get_custom_mail_instructors_url(self):
        return reverse("activities:mail-participants-custom", kwargs={"course": self.pk})

    def get_delete_url(self):
        return reverse("backend:course-delete", kwargs={"course": self.pk})

    def get_duplicate_url(self):
        return reverse("backend:course-create") + f"?source={self.pk}"

    def get_js_export_url(self):
        return reverse("backend:course-js-export", kwargs={"course": self.pk})

    def get_js_csv(self, filelike):
        course_to_js_csv(self, filelike)

    def get_mail_instructors_url(self):
        return reverse("backend:course-mail-instructors", kwargs={"course": self.pk})

    def get_mail_infos_url(self):
        return reverse("activities:mail-instructors", kwargs={"course": self.pk})

    def get_mail_confirmation_url(self):
        return reverse("backend:course-mail-confirmation", kwargs={"course": self.pk})

    def get_period_text(self):
        if self.start_date.year == self.end_date.year:
            if self.start_date.month == self.end_date.month:
                return _date(self.start_date, "F Y")
            return _date(self.start_date, "F") + " - " + _date(self.end_date, "F Y")
        return _date(self.start_date, "F Y") + " - " + _date(self.end_date, "F Y")

    def get_sessions(self):
        return self.sessions.all()

    def get_update_url(self):
        return reverse("backend:course-update", kwargs={"course": self.pk})

    def get_xls_export_url(self):
        return reverse("backend:course-xls-export", kwargs={"course": self.pk})

    def save(self, *args, **kwargs):
        if settings.KEPCHUP_EXPLICIT_SESSION_DATES:
            self.update_dates_from_sessions(commit=False)
        if self.age_min and self.start_date:
            self.min_birth_date = self.start_date - relativedelta(years=self.age_min)
        if self.age_max and self.start_date:
            # if we say up to 6 years old, we want to include children of 6 1/2 years old, hence the +1
            self.max_birth_date = self.start_date - relativedelta(years=self.age_max + 1)
        self.update_nb_participants()  # useful if max participants number has been changed
        super().save(*args, **kwargs)

    def send_places_available_reminder(self):
        from ..tasks import send_places_available_reminder as send_places_available_reminder_task

        if not settings.KEPCHUP_ENABLE_WAITING_LISTS:
            # Feature needs to be activated to send a reminder
            return
        if self.full:
            # No need to send a reminder if the course is full
            return
        if not self.waiting_slots.exists():
            # No need to send a reminder if there are no waiting persons
            return
        if (
            self.places_available_reminder_sent_on
            and self.places_available_reminder_sent_on
            >= timezone.now() - timedelta(hours=settings.KEPCHUP_WAITING_LIST_REMINDER_HOURS)
        ):
            # No need to send a reminder if one was sent less than 24 hours ago
            return
        send_places_available_reminder_task.delay(self.pk)

    def update_dates_from_sessions(self, commit=True):
        dates = self.sessions.values_list("date", flat=True)
        if len(dates):
            self.start_date = min(dates)
            self.end_date = max(dates)
            self.day = self.start_date.isoweekday()
            self.number_of_sessions = len(dates)
        else:
            self.start_date = None
            self.end_date = None
            self.number_of_sessions = 0
        if commit:
            self.save()

    def update_nb_participants(self):
        # Registration has a custom manager that only displays non canceled registrations.
        # Therefore, those only appear in admin, but not anywhere else.
        self.nb_participants = self.participants.count()

    def update_registrations(self, last_registration):
        self.nb_participants = self.participants.count()
        self.save(update_fields=["nb_participants"])

    def __str__(self):
        base = "%(invisible)s%(activity)s (%(number)s): %(fullness)s"
        if self.full:
            fullness = _("Course full")
        else:
            fullness = _("%(available)s out of %(total)s places remaining") % {
                "available": self.available_places,
                "total": self.max_participants,
            }
        return base % {
            "invisible": not self.visible and _("Invisible") + " - " or "",
            "activity": self.activity.name,
            "number": self.number,
            "fullness": fullness,
        }


class CoursesInstructors(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    instructor = models.ForeignKey("profiles.FamilyUser", on_delete=models.CASCADE)
    function = models.ForeignKey("payroll.Function", on_delete=models.SET_NULL, null=True, blank=True)
    contract_number = models.CharField(
        _("Contract number"),
        max_length=30,
        unique=False,
        blank=True,
        null=True,
        default=None,
    )

    class Meta:
        constraints = [
            # 1. Instructor cannot appear twice in the same course
            models.UniqueConstraint(
                fields=["course", "instructor"],
                name="unique_course_instructor",
            ),
            # 2. Contract number unique per instructor + function
            models.UniqueConstraint(
                fields=["instructor", "function"],
                name="unique_instructor_function_single_contract_number",
                condition=~models.Q(contract_number__isnull=True),
            ),
        ]

    def save(self, *args, **kwargs):
        # We don't want to store empty strings, for Postgres NULL != NULL
        # => we can have multiple NULL values but not
        # multiple empty string values.
        if self.contract_number == "":
            self.contract_number = None
        super().save(*args, **kwargs)


class TemplatedEmailReceipt(TimeStampedModel):
    TYPE = Choices(
        ("convocation", _("Convocation to the course")),
        ("need_confirmation", _("Need parent confirmation")),
        ("not_paid", _("Payment reminder")),
        ("instructors", _("Documents for course instructor")),
    )
    type = models.CharField(_("Email type"), choices=TYPE, max_length=30)
    course = models.ForeignKey(
        "Course", related_name="email_receipts", null=True, blank=True, on_delete=models.CASCADE
    )

    class Meta:
        ordering = ("-created",)
