# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import connection, transaction
from django.db import connections

from absences.models import Session
from activities.models import CoursesInstructors
from backend.models import YearTenant
from profiles.models import FamilyUser
from registrations.models import Bill, Child, RegistrationsProfile


def replace_id(source, destination, source_database):
    """
    Replace user source by user destination in source_database
    :param source:
    :param destination:
    :param source_database:
    :return:
    """
    print('Update {} to {} in {}'.format(source.id, destination.id, source_database))
    connection.set_schema_to_public()
    email = destination.email
    destination.email = destination.email + '.com'
    destination.is_active = source.is_active
    destination.is_admin = source.is_admin
    destination.is_manager = source.is_manager
    destination.last_login = source.last_login
    destination.save(using=source_database, sync=False)
    _connection = connections[source_database]
    # At this point we have twice the same user

    with _connection.cursor() as cursor:
        for tenant in YearTenant.objects.using(source_database).all():
            print('Updating for period {}'.format(tenant.schema_name))
            cursor.execute(
                "UPDATE {}.absences_session SET instructor_id='{}' WHERE instructor_id='{}'".format(
                    tenant.schema_name, str(destination.id), str(source.id))
            )
            cursor.execute(
                "UPDATE {}.activities_coursesinstructors SET instructor_id='{}' WHERE instructor_id='{}'".format(
                    tenant.schema_name, str(destination.id), str(source.id))
            )
            cursor.execute(
                "UPDATE {}.registrations_bill SET family_id='{}' WHERE family_id='{}'".format(
                    tenant.schema_name, str(destination.id), str(source.id))
            )
            cursor.execute(
                "UPDATE {}.registrations_child SET family_id='{}' WHERE family_id='{}'".format(
                    tenant.schema_name, str(destination.id), str(source.id))
            )
            cursor.execute(
                "UPDATE {}.registrations_registrationsprofile SET user_id='{}' WHERE user_id='{}'".format(
                    tenant.schema_name, str(destination.id), str(source.id))
                )
        cursor.execute("DELETE from public.profiles_familyuser where id='%s'" % source.id)

    destination.email = email
    destination.save(using=source_database, sync=False)


default_db = {}
for user in FamilyUser.objects.using('default').all():
    default_db[user.email] = user

other_db = {}
for user in FamilyUser.objects.using('other').all():
    other_db[user.email] = user

for email, user in default_db.items():
    if email in other_db:
        # User available in both dbs. We need to update one
        other_user = other_db[user.email]
        if other_user.id != user.id:
            if user.last_login is None and other_user.last_login:
                # choose other_user
                replace_id(source=user, destination=other_user, source_database='default')
                # Replace user source by user destination in source_database
                other_user = FamilyUser.objects.using('other').get(pk=other_user.pk)
                other_user.save(using='other', sync=True)
            elif other_user.last_login is None:
                # choose user
                replace_id(source=other_user, destination=user, source_database='other')
                # Replace user source by user destination in source_database
                user = FamilyUser.objects.using('default').get(pk=user.pk)
                user.save(using='default', sync=True)
            elif user.last_login < other_user.last_login:
                # choose other_user
                replace_id(source=user, destination=other_user, source_database='default')
                # Replace user source by user destination in source_database
                other_user = FamilyUser.objects.using('other').get(pk=other_user.pk)
                other_user.save(using='other', sync=True)
            else:
                # chooser user
                replace_id(source=other_user, destination=user, source_database='other')
                # Replace user source by user destination in source_database
                user = FamilyUser.objects.using('default').get(pk=user.pk)
                user.save(using='default', sync=True)
        else:
            # Already migrated, we just ensure one is saved to master
            user.save(using='default', sync=True)
    else:
        # User only available in default db => save it to master
        user.save(using='default', sync=True)


for email, user in other_db.items():
    # noinspection DuplicatedCode
    if user.email in default_db:
        # already handled above
        pass
    else:
        # user only exists in db1, insert into master
        user.save(using='other', sync=True)
