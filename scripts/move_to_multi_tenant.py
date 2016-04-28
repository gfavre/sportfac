from datetime import datetime, timedelta

from django.conf import settings
from constance.admin import config

from backend.models import YearTenant, Domain

tenant = YearTenant(
    schema_name='public',
    start_date=config.START_REGISTRATION,
    end_date=config.START_REGISTRATION + timedelta(days=365)
)
tenant.save()
    
domain = Domain()
domain.domain = settings.DEFAULT_TENANT_NAME
domain.tenant = tenant
domain.is_primary = True
domain.save()
    


from datetime import datetime, timedelta

from django.conf import settings
from constance.admin import config

from backend.models import YearTenant, Domain

tenant = YearTenant(
    schema_name='year_2015_2016',
    start_date=datetime(2015, 8, 1),
    end_date=datetime(2016, 7, 31)
)
tenant.save()
    
domain = Domain()
domain.domain = '2015-2016'
domain.tenant = tenant
domain.is_primary = True
domain.save()
    


tenant = YearTenant(
    schema_name='year_2016_2017',
    start_date=datetime(2016, 8, 1),
    end_date=datetime(2017, 7, 31)
)
tenant.save()
    
domain = Domain()
domain.domain = '2016-2017'
domain.tenant = tenant
domain.is_primary = True
domain.save()
    
