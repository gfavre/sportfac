from __future__ import annotations

import os
import socket
from datetime import datetime

from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.contrib.sessions.models import Session
from django.db import connection
from django.db import transaction
from django.utils import timezone

from registrations.utils import load_children
from sportfac.decorators import respects_language

from .models import Domain
from .models import YearTenant
from .tenant_utils import copy_activities
from .tenant_utils import copy_children
from .tenant_utils import copy_payroll_functions


logger = get_task_logger(__name__)


@shared_task
@respects_language
def create_tenant(
    start: str,
    end: str,
    copy_activities_from_id: int | None = None,
    copy_children_from_id: int | None = None,
    user_id: int | None = None,
) -> None:
    """
    Create a new tenant for the given period and optionally copy data from others.

    Args:
        start: Start date (YYYY-MM-DD).
        end: End date (YYYY-MM-DD).
        copy_activities_from_id: YearTenant id to copy activities from.
        copy_children_from_id: YearTenant id to copy children/schools from.
        user_id: Optional user id for logging/audit.
    """
    if user_id:
        logger.debug(f"User {user_id} is logged in")
    start_dt = datetime.strptime(start, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end, "%Y-%m-%d").date()

    connection.set_schema_to_public()
    with transaction.atomic():
        destination, _ = YearTenant.objects.get_or_create(
            schema_name=f"period_{start_dt:%Y%m%d}_{end_dt:%Y%m%d}",
            defaults={"start_date": start_dt, "end_date": end_dt, "status": YearTenant.STATUS.creating},
        )
        destination.create_schema(check_if_exists=True)
        Domain.objects.get_or_create(tenant=destination, domain=f"{start_dt:%Y%m%d}-{end_dt:%Y%m%d}")

    # Optional payroll copy. Must be before activities
    if settings.KEPCHUP_ENABLE_PAYROLLS and copy_activities_from_id:
        try:
            source = YearTenant.objects.get(pk=copy_activities_from_id)
            copy_payroll_functions(source, destination, logger=logger)
        except YearTenant.DoesNotExist:
            logger.warning("YearTenant %s not found for payroll copy", copy_activities_from_id)

    # Copy activities
    if copy_activities_from_id:
        try:
            source = YearTenant.objects.get(pk=copy_activities_from_id)
            destination.status = YearTenant.STATUS.copying
            destination.save(update_fields=["status"])
            copy_activities(source, destination, logger=logger)
        except YearTenant.DoesNotExist:
            logger.warning("YearTenant %s not found for activities copy", copy_activities_from_id)

    # Copy children
    if copy_children_from_id:
        try:
            source = YearTenant.objects.get(pk=copy_children_from_id)
            destination.status = YearTenant.STATUS.copying
            destination.save(update_fields=["status"])
            copy_children(source, destination, logger=logger)
        except YearTenant.DoesNotExist:
            logger.warning("YearTenant %s not found for children copy", copy_children_from_id)

    destination.status = YearTenant.STATUS.ready
    destination.save(update_fields=["status"])


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
    get_task_logger(__name__).info("Importing children from %s", filepath)
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


@shared_task
def log_everyone_out(exceptions=None):
    """
    Log out all users by deleting all sessions.
    This is useful when switching tenants or for maintenance tasks.
    """
    queryset = Session.objects.all()
    if exceptions:
        logger.info("Logging out all users except those in exceptions: %s", exceptions)
        queryset = queryset.exclude(session_key__in=exceptions)
    queryset.delete()
    logger.info("All users have been logged out.")
