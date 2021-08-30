# -*- coding: utf-8 -*-
from profiles.models import FamilyUser
from registrations.models import Registration

for fam in FamilyUser.objects.all():
    registrations = Registration.objects.filter(child__family=fam, status='')
    to_pay = sum([registration.get_price_category()[0] for registration in registrations])
    paid = sum([bill.total for bill in fam.bills.filter(status='paid')])
    if to_pay != paid:
        print('\t'.join((fam.full_name, str(paid), str(to_pay))))

