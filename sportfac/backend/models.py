from datetime import date

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models

from django_tenants.models import TenantMixin, DomainMixin


class YearTenant(TenantMixin):
    start_date = models.DateField(null=False)
    end_date = models.DateField(null=False)
    created_on = models.DateTimeField(auto_now_add=True)
    
    def __unicode__(self):
        if self.start_date.year != self.end_date.year:
            return '%i-%i' % (self.start_date.year, self.end_date.year)
        return '%i.%i-%i.%i %i' % (self.start_date.day, self.start_date.month, 
                                   self.end_date.day, self.end_date.month,
                                   self.end_date.year)
    
    @property
    def is_production(self):
        return self.domains.first().is_current
    
    @property
    def is_past(self):
        return self.end_date < date.today()
    
    @property
    def is_future(self):
        return self.start_date > date.today()
    
    class Meta:
        ordering = ('start_date',)

class Domain(DomainMixin):
    is_current = models.BooleanField(default=False)
    
    def __unicode__(self):
        if self.is_current:
            return '[default domain] ' + self.domain
        return self.domain