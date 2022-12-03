from __future__ import absolute_import

from datetime import datetime, timedelta

from django.conf import settings

from backend.models import Domain, YearTenant
from constance.admin import config


tenant = YearTenant(
    schema_name="period_20150801_20160731",
    start_date=datetime(2015, 8, 1),
    end_date=datetime(2016, 7, 31),
)
tenant.save()
tenant.create_schema(check_if_exists=True)

domain = Domain()
domain.domain = "2015-2016"
domain.tenant = tenant
domain.is_primary = True
domain.save()


tenant = YearTenant(
    schema_name="period_20160801_20170731",
    start_date=datetime(2016, 8, 1),
    end_date=datetime(2017, 7, 31),
)
tenant.create_schema(check_if_exists=True)
tenant.save()

domain = Domain()
domain.domain = "2016-2017"
domain.tenant = tenant
domain.is_primary = True
domain.save()
