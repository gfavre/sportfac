from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import Group
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.conf import settings
from django.db import transaction

from activities.models import Course
from mailer.pdfutils import PDFRenderer
from . import INSTRUCTORS_GROUP, MANAGERS_GROUP


class AbsencePDFRenderer(PDFRenderer):
    message_template = 'backend/course/absences.html'
    rasterizer = settings.PHANTOMJS_RASTERIZE_PORTRAIT


class AbsencesPDFRenderer(PDFRenderer):
    message_template = 'backend/course/multiple-absences.html'
    rasterizer = settings.PHANTOMJS_RASTERIZE_PORTRAIT


@transaction.atomic
def clean_instructors():
    for instructor in Group.objects.get(name=INSTRUCTORS_GROUP).user_set.all():
        instructor.is_instructor = False

    for course in Course.objects.prefetch_related('instructors').all():
        for instructor in course.instructors.all():
            instructor.is_instructor = True


def manager_required(fct=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None):
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.groups.filter(name=MANAGERS_GROUP).exists() or u.is_superuser,
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if fct:
        return actual_decorator(fct)
    return actual_decorator
