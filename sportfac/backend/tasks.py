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
from registrations.models import Child
from registrations.utils import load_children
from sportfac.decorators import respects_language
from .models import YearTenant, Domain
from .utils import clean_instructors
from . import MANAGERS_GROUP


logger = get_task_logger(__name__)


@shared_task
@respects_language
def create_tenant(new_tenant_id, copy_activities_from_id=None, copy_children_from_id=None, user_id=None):
    try:
        user = FamilyUser.objects.get(pk=user_id)
        logger.info('New tenant {}, copy activities from {}, copy children from {}, user={}'.format(
            new_tenant_id, copy_activities_from_id, copy_children_from_id, user
        ))
    except user.DoesNotExist:
        logger.info('New tenant {}, copy activities from {}, copy children from {}'.format(
            new_tenant_id, copy_activities_from_id, copy_children_from_id
        ))

    connection.set_schema_to_public()
    destination_tenant = YearTenant.objects.get(pk=new_tenant_id)
    destination_tenant.create_schema(check_if_exists=True)
    logger.info('Created schema for period %s-%s' % (destination_tenant.start_date.isoformat(),
                                                     destination_tenant.end_date.isoformat()))
    if copy_activities_from_id:
        logger.info('Beginning copy of activities')
        try:
            copy_from = YearTenant.objects.get(id=copy_activities_from_id)
            destination_tenant.status = YearTenant.STATUS.copying
            destination_tenant.save()

            connection.set_tenant(copy_from)
            f = NamedTemporaryFile(suffix='.json', delete=False)
            call_command('dumpdata', 'activities', output=f.name)
            f.close()
            logger.debug('Dumped activities from source')

            connection.set_tenant(destination_tenant)
            call_command('loaddata', f.name)
            os.remove(f.name)
            logger.info('Populated activities for period {}-{}'.format(
                destination_tenant.start_date.isoformat(),
                destination_tenant.end_date.isoformat()
            ))

            Course.objects.all().update(uptodate=False)
            logger.debug('Set all courses to not up-to-date in destination')

        except YearTenant.DoesNotExist:
            logger.warning('Year tenant {} (source) does not exist'.format(copy_from))

    if copy_children_from_id:
        logger.info('Beginning copy of children')
        try:
            copy_from = YearTenant.objects.get(id=copy_children_from_id)
            destination_tenant.status = YearTenant.STATUS.copying
            destination_tenant.save()

            connection.set_tenant(copy_from)
            f = NamedTemporaryFile(suffix='.json', delete=False)
            call_command('dumpdata', 'schools', output=f.name)
            f.close()
            logger.debug('Dumped schools from source')

            connection.set_tenant(destination_tenant)
            call_command('loaddata', f.name)
            os.remove(f.name)
            logger.info('Populated schools for period {}-{}'.format(
                destination_tenant.start_date.isoformat(),
                destination_tenant.end_date.isoformat()
            ))

            connection.set_tenant(copy_from)
            f = NamedTemporaryFile(suffix='.json', delete=False)
            call_command('dumpdata', 'registrations.Child', output=f.name)
            f.close()
            logger.debug('Dumped children from source: {}'.format(f.name))

            connection.set_tenant(destination_tenant)
            call_command('loaddata', f.name)
            os.remove(f.name)
            logger.debug('Populated children for period {}-{}'.format(
                destination_tenant.start_date.isoformat(),
                destination_tenant.end_date.isoformat()
            ))

            Child.objects.all().update(status=Child.STATUS.imported)
            logger.debug('Set all children to not up-to-date in destination')

        except YearTenant.DoesNotExist:
            logger.warning('Year tenant {} (source) does not exist'.format(copy_from))

    destination_tenant.status = YearTenant.STATUS.ready
    destination_tenant.save()
    logger.info('Created / populated period {}-{}'.format(
        destination_tenant.start_date.isoformat(),
        destination_tenant.end_date.isoformat())
    )
    if user:
        msg = _("The period %(start)s-%(end)s is ready to be used. "
                "You can preview it at the %(link_start)speriod management interface%(link_end)s.")
        params = {'start': destination_tenant.start_date.isoformat(),
                  'end': destination_tenant.end_date.isoformat(),
                  'link_start': format_html('<a href="{}">', reverse('backend:year-list')),
                  'link_end': format_html('</a>')}
        messages.success(user, mark_safe(msg % params))
        logger.debug('Warned user for period activation')


@shared_task
@transaction.atomic
@respects_language
def update_current_tenant():
    now = timezone.now()
    current_domain = Domain.objects.filter(is_current=True).first()
    possible_new_tenants = YearTenant.objects.filter(start_date__lte=now,
                                                     end_date__gte=now,
                                                     status=YearTenant.STATUS.ready) \
        .exclude(domains=current_domain) \
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
    with open(filepath) as filelike:
        try:
            (nb_created, nb_updated) = load_children(filelike)
            status = constants.SUCCESS
            message = _("Children import successful. "
                        "%(added)s children have been added, %(updated)s have been updated") % {
                          'added': nb_created,
                          'updated': nb_updated
                      }
        except ValueError as err:
            status = constants.ERROR
            message = err.message

    try:
        user = FamilyUser.objects.get(pk=user_id)
        message_user(user, message, status)
    except FamilyUser.DoesNotExist:
        pass
