# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-07-13 14:48
from django.conf import settings
from django.db import migrations, models


def fill_instructor_uuid(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    Session = apps.get_model("absences", "Session")
    for obj in (
        Session.objects.using(db_alias)
        .select_related("instructor")
        .exclude(instructor__isnull=True)
    ):
        obj.instructor_uuid = obj.instructor.uuid
        obj.save()


class Migration(migrations.Migration):

    dependencies = [
        ("absences", "0012_auto_20190305_0533"),
        ("profiles", "0013_add_uuid"),
    ]

    operations = [
        migrations.AddField(
            model_name="session",
            name="instructor_uuid",
            field=models.UUIDField(null=True),
        ),
        migrations.RunPython(fill_instructor_uuid, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="session",
            name="instructor",
        ),
    ]
