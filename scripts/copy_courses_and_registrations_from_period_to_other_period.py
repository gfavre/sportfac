from __future__ import absolute_import, print_function

import json
from tempfile import NamedTemporaryFile

from django.core import serializers
from django.db import connection, transaction

from activities.models import Activity, Course
from backend.models import YearTenant
from registrations.models import Child, Registration
from six.moves import input


source_schema = "period_20210701_20220630"
destination_schema = "period_20220822_20230827"
source_tenant = YearTenant.objects.get(schema_name=source_schema)
destination_tenant = YearTenant.objects.get(schema_name=destination_schema)
courses_to_copy = ["EN04"]

# on pourrait dumpdata de registrations et courses, et filtrer sur les cours à copier

for course_number in courses_to_copy:
    connection.set_tenant(source_tenant)
    source_course = Course.objects.get(number=course_number)
    children = serializers.serialize(
        "json", [reg.child for reg in source_course.participants.all()]
    )
    connection.set_tenant(destination_tenant)
    destination_course = Course.objects.get(number=course_number)
    for child in serializers.deserialize("json", children):
        print(("create reg for {} on {}".format(child.object, destination_course)))
        if input("Do for {}? [Y/n]".format(child.object)) != "n":
            child.object.pk = None
            child.object.save()
            print(("created {}".format(child.object)))
            Registration.objects.create(
                child=child.object, course=destination_course, paid=True, status="confirmed"
            )
