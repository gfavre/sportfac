from django.db import connection, transaction
from django.contrib.auth.models import Group

from backend import INSTRUCTORS_GROUP
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


