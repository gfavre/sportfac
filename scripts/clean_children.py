# -*- coding: utf-8 -*-
from registrations.models import Child
from profiles.models import FamilyUser
import unicodedata



def clean_name(name):
    name = name.strip()
    return unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode("utf-8")


for f in FamilyUser.objects.all():
    if f.children.count() <= 1:
        continue

    to_conserve = []
    to_conserve_names = []
    for child in f.children.all():
        if child.registrations.exists():
            to_conserve.append(child.pk)
            to_conserve_names.append(clean_name(child.get_full_name()))

    if f.children.count() != len(to_conserve):
        print f.children_names
    names = []
    for child in f.children.exclude(pk__in=to_conserve):
        name = clean_name(child.get_full_name())
        if name in to_conserve_names:
            child.delete()
        if name in names:
            child.delete()
        names.append(name)