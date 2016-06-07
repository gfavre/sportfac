from __future__ import absolute_import
from datetime import datetime
import os
from tempfile import NamedTemporaryFile

from django.core.management import call_command
from django.contrib.sessions.models import Session
from django.db import connection
from django.db import transaction
from django.utils import timezone

from celery import shared_task
from celery.utils.log import get_task_logger

from backend.models import YearTenant, Domain
from activities.models import Course

logger = get_task_logger(__name__)


@shared_task
def create_tenant(start_date, end_date, new_tenant_id, copy_from_id=None):
    connection.set_schema_to_public()
    tenant = YearTenant.objects.get(pk=new_tenant_id)
    tenant.create_schema(check_if_exists=True)

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


@shared_task
@transaction.atomic
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
        else:
            current_domain.is_current = False
            current_domain.save()
            new_domain = possible_new_tenants.first().domains.first()
            new_domain.is_current = True
            new_domain.save()
            # log out everyone
            Session.objects.all().delete()
        
        