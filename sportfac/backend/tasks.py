import os
import socket
from datetime import datetime
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.db import connection, transaction
from django.utils import timezone

from celery import shared_task
from celery.utils.log import get_task_logger

from activities.models import Course
from profiles.models import FamilyUser
from registrations.models import Child
from registrations.utils import load_children
from sportfac.decorators import respects_language
from .models import Domain, YearTenant


logger = get_task_logger(__name__)


@shared_task
@respects_language
def create_tenant(start, end, copy_activities_from_id=None, copy_children_from_id=None, user_id=None):
    start = datetime.strptime(start, "%Y-%m-%d").date()
    end = datetime.strptime(end, "%Y-%m-%d").date()
    connection.set_schema_to_public()
    with transaction.atomic():
        destination_tenant, created = YearTenant.objects.get_or_create(
            schema_name="period_{}_{}".format(start.strftime("%Y%m%d"), end.strftime("%Y%m%d")),
            defaults={"start_date": start, "end_date": end, "status": YearTenant.STATUS.creating},
        )

        destination_tenant.create_schema(check_if_exists=True)
        logger.info(
            "Created schema for period %s-%s"
            % (destination_tenant.start_date.isoformat(), destination_tenant.end_date.isoformat())
        )
        Domain.objects.get_or_create(
            tenant=destination_tenant,
            domain="{}-{}".format(start.strftime("%Y%m%d"), end.strftime("%Y%m%d")),
        )
    try:
        user = FamilyUser.objects.get(pk=user_id)
        logger.info(
            "New tenant {}, copy activities from {}, copy children from {}, user={}".format(
                destination_tenant.schema_name,
                copy_activities_from_id,
                copy_children_from_id,
                user,
            )
        )
    except FamilyUser.DoesNotExist:
        user = None
        logger.info(
            "New tenant {}, copy activities from {}, copy children from {}".format(
                destination_tenant.schema_name, copy_activities_from_id, copy_children_from_id
            )
        )

    if copy_activities_from_id:
        logger.info("Beginning copy of activities")
        try:
            copy_from = YearTenant.objects.get(id=copy_activities_from_id)
            destination_tenant.status = YearTenant.STATUS.copying
            destination_tenant.save()

            connection.set_tenant(copy_from)
            f = NamedTemporaryFile(suffix=".json", delete=False)
            call_command("dumpdata", "activities", "payroll.Function", output=f.name)
            f.close()
            logger.debug("Dumped activities from source")

            connection.set_tenant(destination_tenant)
            call_command("loaddata", f.name)
            os.remove(f.name)
            logger.info(
                "Populated activities for period {}-{}".format(
                    destination_tenant.start_date.isoformat(),
                    destination_tenant.end_date.isoformat(),
                )
            )

            Course.objects.all().update(uptodate=False, nb_participants=0)
            logger.debug("Set all courses to not up-to-date in destination")

        except YearTenant.DoesNotExist:
            logger.warning(f"Year tenant {copy_activities_from_id} (source) does not exist")

    if copy_children_from_id:
        logger.info("Beginning copy of children")
        try:
            copy_from = YearTenant.objects.get(id=copy_children_from_id)
            destination_tenant.status = YearTenant.STATUS.copying
            destination_tenant.save()

            connection.set_tenant(copy_from)
            f = NamedTemporaryFile(suffix=".json", delete=False)
            call_command("dumpdata", "schools", output=f.name)
            f.close()
            logger.debug("Dumped schools from source")

            connection.set_tenant(destination_tenant)
            call_command("loaddata", f.name)
            os.remove(f.name)
            logger.info(
                "Populated schools for period {}-{}".format(
                    destination_tenant.start_date.isoformat(),
                    destination_tenant.end_date.isoformat(),
                )
            )

            connection.set_tenant(copy_from)
            f = NamedTemporaryFile(suffix=".json", delete=False)
            call_command("dumpdata", "registrations.Child", output=f.name)
            f.close()
            logger.debug(f"Dumped children from source: {f.name}")

            connection.set_tenant(destination_tenant)
            call_command("loaddata", f.name)
            os.remove(f.name)
            logger.debug(
                "Populated children for period {}-{}".format(
                    destination_tenant.start_date.isoformat(),
                    destination_tenant.end_date.isoformat(),
                )
            )

            Child.objects.all().update(status=Child.STATUS.imported)
            logger.debug("Set all children to not up-to-date in destination")

        except YearTenant.DoesNotExist:
            logger.warning(f"Year tenant {copy_children_from_id} (source) does not exist")

    if settings.KEPCHUP_ENABLE_PAYROLLS:
        try:
            copy_from = YearTenant.objects.get(id=copy_activities_from_id)
            destination_tenant.status = YearTenant.STATUS.copying
            destination_tenant.save()

            connection.set_tenant(copy_from)
            f = NamedTemporaryFile(suffix=".json", delete=False)
            call_command("dumpdata", "payroll.Function", output=f.name)
            f.close()
            connection.set_tenant(destination_tenant)
            call_command("loaddata", f.name)
            os.remove(f.name)
            logger.debug(
                "Populated functions for period {}-{}".format(
                    destination_tenant.start_date.isoformat(),
                    destination_tenant.end_date.isoformat(),
                )
            )
        except YearTenant.DoesNotExist:
            logger.warning(f"Year tenant {copy_activities_from_id} (source) does not exist")

    destination_tenant.status = YearTenant.STATUS.ready
    destination_tenant.save()
    logger.info(
        "Created / populated period {}-{}".format(
            destination_tenant.start_date.isoformat(), destination_tenant.end_date.isoformat()
        )
    )
    # if user:
    #     msg = _(
    #         "The period %(start)s-%(end)s is ready to be used. "
    #         "You can preview it at the %(link_start)speriod management interface%(link_end)s."
    #     )
    #     params = {
    #         "start": destination_tenant.start_date.isoformat(),
    #         "end": destination_tenant.end_date.isoformat(),
    #         "link_start": format_html('<a href="{}">', reverse("backend:year-list")),
    #         "link_end": format_html("</a>"),
    #     }


@shared_task
@transaction.atomic
@respects_language
def update_current_tenant():
    now = timezone.now()
    current_domain = Domain.objects.filter(is_current=True).first()
    possible_new_tenants = (
        YearTenant.objects.filter(start_date__lte=now, end_date__gte=now, status=YearTenant.STATUS.ready)
        .exclude(domains=current_domain)
        .order_by("start_date", "end_date")
    )

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

        # for user in FamilyUser.objects.filter(is_active=True, is_manager=True):
        #     msg = _("The active period has been automatically changed to %(start)s - %(end)s")
        #     params = {
        #         "start": new_domain.tenant.start_date.isoformat(),
        #         "end": new_domain.tenant.end_date.isoformat(),
        #     }
        #     # messages.info(user, msg % params)

        connection.set_tenant(new_domain.tenant)


@shared_task
@respects_language
def import_children(filepath, tenant_id, user_id=None):
    tenant = YearTenant.objects.get(pk=tenant_id)
    connection.set_tenant(tenant)
    with open(filepath, "rb") as filelike:
        try:
            (nb_created, nb_updated) = load_children(filelike)
            # status = messages.constants.SUCCESS
            # message = _(
            #     "Children import successful. " "%(added)s children have been added, %(updated)s have been updated"
            # ) % {"added": nb_created, "updated": nb_updated}
        except ValueError as err:
            # status = messages.constants.ERROR
            # message = err
            logger.exception("Error while importing children", exc_info=err)

    # try:
    #     user = FamilyUser.objects.get(pk=user_id)
    #     # message_user(user, message, status)
    # except FamilyUser.DoesNotExist:
    #     pass


@shared_task
def celery_health_check():
    return {"hostname": socket.gethostname(), "pid": os.getpid(), "status": "ok"}
