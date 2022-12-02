# -*- coding: utf-8 -*-
from __future__ import absolute_import
from django.db import IntegrityError

from celery import shared_task
from celery.utils.log import get_task_logger

from sportfac.database_router import MASTER_DB, LOCAL_DB
from .models import FamilyUser

logger = get_task_logger(__name__)


@shared_task
def save_to_master(user_id, source=LOCAL_DB):
    user = FamilyUser.objects.using(source).get(pk=user_id)
    try:
        user.save(create_profile=False, sync=False, using=MASTER_DB)
    except IntegrityError:
        logger.info("User already exists in master DB")


@shared_task
def sync_from_master():
    local_last_updated_family = FamilyUser.objects.order_by('modified').last()
    to_update = FamilyUser.objects.using(MASTER_DB).all()
    if local_last_updated_family:
        to_update = to_update.filter(modified__gt=local_last_updated_family.modified)
    for user in to_update:
        try:
            local_user = FamilyUser.objects.using(LOCAL_DB).get(pk=user.pk)
            user.is_admin = local_user.is_admin
            user.is_active = local_user.is_active
            user.is_manager = local_user.is_manager
            user.last_login = local_user.last_login
        except FamilyUser.DoesNotExist:
            # The user exists on master (created on other instance) but not locally
            user.is_admin = False
            user.is_manager = False
        user.save(using=LOCAL_DB, sync=False)


# TODO: script d'import initial intelligent
