from __future__ import absolute_import
from datetime import date
import os
from tempfile import NamedTemporaryFile

from django.db import connection

from celery import shared_task
from celery.utils.log import get_task_logger

from backend.models import YearTenant
from activities.models import Course

logger = get_task_logger(__name__)


@shared_task
def create_tenant(start_date, end_date, copy_from_id=None):
    connection.set_schema_to_public()
    tenant = YearTenant(
        schema_name='period_%s_%s' % (start_date, end_date),
        start_date=date.strptime(start_date, '%Y%m%d'),
        end_date=date.strptime(end_date, '%Y%m%d'),
        status=YearTenant.STATUS.creating
    )
    tenant.save()
    tenant.create_schema(check_if_exists=True)

    domain = Domain.objects.create(
        is_primary=False,
        domain='%s-%s' % (start_date, end_date),
        tenant=tenant
    )
    if copy_from_id:
        try:
            copy_from = YearTenant.objects.get(id=copy_from_id)
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
        except YearTenant.DoesNotExist:
            pass                
    tenant.status = YearTenant.STATUS.ready
    tenant.save()