from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import Group
from django.contrib.auth import REDIRECT_FIELD_NAME

from django.db import transaction

from backend import INSTRUCTORS_GROUP, MANAGERS_GROUP
from activities.models import Course

@transaction.atomic
def clean_instructors():
    for instructor in Group.objects.get(name=INSTRUCTORS_GROUP).user_set.all():
        instructor.is_instructor = False
    
    for course in Course.objects.prefetch_related('instructors').all():
        for instructor in course.instructors.all():
            instructor.is_instructor = True

def copy_courses(source_tenant, destination_tenant):
    pass


def manager_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None):
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.groups.filter(name=MANAGERS_GROUP).exists() or u.is_superuser,
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator