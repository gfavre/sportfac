from django.db import models

from django_tenants.models import TenantMixin, DomainMixin


class YearTenant(TenantMixin):
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)
    created_on = models.DateTimeField(auto_now_add=True)

class Domain(DomainMixin):
    pass