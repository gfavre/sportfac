# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

from profiles.models import FamilyUser
from registrations.models import Registration


for family in FamilyUser.objects.all():
    if family.city.lower().strip() == "prangins":
        family.zipcode = "1197"
        family.city = "Prangins"
        family.save()
    elif family.city.lower().strip() == "nyon":
        family.zipcode = "1260"
        family.city = "Nyon"
        family.save()


prangins_families = set()
prangins_children = set()
registrations = set()
for registration in Registration.objects.exclude(
    status__in=(Registration.STATUS.canceled, Registration.STATUS.waiting)
):
    if registration.child.family.zipcode == "1197":
        registrations.add(registration)
        prangins_families.add(registration.child.family)
        prangins_children.add(registration.child)

print(
    (
        "{} élèves pranginois issus de {} familles différentes et totalisant {} inscriptions sont inscrits aux sports "
        "scolaires facultatifs et suivent des cours tant à Prangins que sur Nyon".format(
            len(prangins_children), len(prangins_families), len(registrations)
        )
    )
)
