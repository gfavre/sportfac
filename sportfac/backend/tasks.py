from __future__ import absolute_import
import os
from tempfile import NamedTemporaryFile

from django.core.management import call_command
from django.core.urlresolvers import reverse
from django.contrib.auth.models import Group
from django.contrib.messages import constants
from django.contrib.sessions.models import Session
from django.db import connection, transaction
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from async_messages import messages, message_user
from celery import shared_task
from celery.utils.log import get_task_logger

from activities.models import Course
from profiles.models import FamilyUser
from registrations.utils import load_children
from sportfac.decorators import respects_language
from .models import YearTenant, Domain
from .utils import clean_instructors
from . import MANAGERS_GROUP

logger = get_task_logger(__name__)


@shared_task
@respects_language
def create_tenant(new_tenant_id, copy_activities_from_id=None, copy_children_from_id=None, user_id=None):
    connection.set_schema_to_public()
    tenant = YearTenant.objects.get(pk=new_tenant_id)
    tenant.create_schema(check_if_exists=True)
    logger.debug('Created schema for period %s-%s' % (tenant.start_date.isoformat(), tenant.end_date.isoformat()))
    if copy_activities_from_id:
        try:
            copy_from = YearTenant.objects.get(id=copy_activities_from_id)
            tenant.status = YearTenant.STATUS.copying
            tenant.save()
            f = NamedTemporaryFile(suffix='.json', delete=False)
            call_command('tenant_command', 'dumpdata', 'activities',
                         output=f.name, schema=copy_from.schema_name)
            f.close()
            call_command('tenant_command', 'loaddata', f.name, schema=tenant.schema_name)
            os.remove(f.name)
            connection.set_tenant(tenant)
            Course.objects.all().update(uptodate=False)
            logger.debug('Populated activities for period %s-%s' %(tenant.start_date.isoformat(), tenant.end_date.isoformat()))
        except YearTenant.DoesNotExist:
            pass

    if copy_children_from_id:
        try:
            copy_from = YearTenant.objects.get(id=copy_children_from_id)
            tenant.status = YearTenant.STATUS.copying
            tenant.save()

            f = NamedTemporaryFile(suffix='.json', delete=False)
            call_command('tenant_command', 'dumpdata', 'schools',
                         output=f.name, schema=copy_from.schema_name)
            f.close()
            call_command('tenant_command', 'loaddata', f.name, schema=tenant.schema_name)
            os.remove(f.name)
            logger.debug('Populated schools for period %s-%s' % (tenant.start_date.isoformat(), tenant.end_date.isoformat()))

            f = NamedTemporaryFile(suffix='.json', delete=False)
            call_command('tenant_command', 'dumpdata', 'registrations.Child',
                         output=f.name, schema=copy_from.schema_name)
            f.close()
            call_command('tenant_command', 'loaddata', f.name, schema=tenant.schema_name)
            os.remove(f.name)

            connection.set_tenant(tenant)
            logger.debug('Populated children for period %s-%s' % (tenant.start_date.isoformat(), tenant.end_date.isoformat()))
        except YearTenant.DoesNotExist:
            pass

    tenant.status = YearTenant.STATUS.ready
    tenant.save()
    logger.info('Created / populated period %s-%s' %(tenant.start_date.isoformat(), tenant.end_date.isoformat()))
    try:
        user = FamilyUser.objects.get(pk=user_id)
        msg = _("The period %(start)s-%(end)s is ready to be used. You can preview it at the %(link_start)speriod management interface%(link_end)s.")
        params = {'start': tenant.start_date.isoformat(),
                  'end': tenant.end_date.isoformat(),
                  'link_start': format_html('<a href="{}">', reverse('backend:year-list')),
                  'link_end': format_html('</a>')}
        messages.success(user, mark_safe(msg % params))
        logger.debug('Warned user for period activation')
    except FamilyUser.DoesNotExist:
        pass



@shared_task
@transaction.atomic
@respects_language
def update_current_tenant():
    now = timezone.now()
    current_domain = Domain.objects.filter(is_current=True).first()
    possible_new_tenants = YearTenant.objects.filter(start_date__lte=now,
                                                     end_date__gte=now,
                                                     status=YearTenant.STATUS.ready)\
                                             .exclude(domains=current_domain)\
                                             .order_by('start_date', 'end_date')

    if possible_new_tenants.count():
        if not (current_domain.tenant.is_past or current_domain.tenant.is_future):
            # do not switch if current tenant is still valid
            return
        current_domain.is_current = False
        current_domain.save()
        new_domain = possible_new_tenants.first().domains.first()
        new_domain.is_current = True
        new_domain.save()
        # log out everyone
        Session.objects.all().delete()

        for user in Group.objects.get(name=MANAGERS_GROUP).user_set.all():
            msg = _("The active period has been automatically changed to %(start)s - %(end)s")
            params = {'start': new_domain.tenant.start_date.isoformat(),
                      'end': new_domain.tenant.end_date.isoformat()}
            messages.info(user, msg % params)

        connection.set_tenant(new_domain.tenant)
        clean_instructors()


@shared_task
@respects_language
def import_children(filepath, tenant_id, user_id=None):
    tenant = YearTenant.objects.get(pk=tenant_id)
    connection.set_tenant(tenant)
    status = ''
    message = ''
    with open(filepath) as filelike:
        try:
            (nb_created, nb_updated) = load_children(filelike)
            status = constants.SUCCESS
            message = _("Children import successful. %(added)s children have been added, %(updated)s have been updated") % {
                'added': nb_created,
                'updated': nb_updated
            }
        except ValueError, msg:
            status = constants.ERROR
            message = msg

    try:
        user = FamilyUser.objects.get(pk=user_id)
        message_user(user, message, status)
    except FamilyUser.DoesNotExist:
        pass
