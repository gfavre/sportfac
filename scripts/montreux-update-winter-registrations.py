
from __future__ import absolute_import, print_function

import six
from activities.models import ExtraNeed
from import_export.formats.base_formats import XLSX
from registrations.models import ChildActivityLevel, ExtraInfo, Registration, Transport

"""
hiver 2023:

Colonnes:
Id Favre	ID LAGAPEO	Nom	Prénom	dossard	NoCar	SSF 22	niveau
3	323386	Grandvuinet	Ilyas	413	4	S 5B	Moyen
"""

fmt = XLSX()
f = open("/home/greg/temp/montreux-hiver-2023.xlsx", fmt.get_read_mode())
dataset = fmt.create_dataset(f.read())
level_extra_key = "Niveau de ski/snowboard"
question = ExtraNeed.objects.get(question_label=level_extra_key)

for (
    registration_id,
    id_lagapeo,
    first_name,
    last_name,
    bib_number,
    transport_name,
    old_level,
    announced_level,
) in dataset:
    try:
        registration = Registration.objects.get(pk=registration_id)
    except Registration.DoesNotExist:
        print(("Missing registration: {}".format(registration_id)))
        continue
    if six.text_type(registration.child.id_lagapeo) != id_lagapeo:
        print(("id_lagapeo coherence: {}/{}".format(registration.child.id_lagapeo, id_lagapeo)))
        continue
    if transport_name:
        transport, created = Transport.objects.get_or_create(name=transport_name)
        if created:
            print(("Created transport {}".format(transport_name)))
        registration.transport = transport
        registration.save()
    if bib_number:
        registration.child.bib_number = bib_number
        registration.child.save()
    if announced_level:
        try:
            answer = registration.extra_infos.get(key=question)
        except:
            answer = ExtraInfo.objects.create(key=question, registration=registration)
        if answer.value != announced_level:
            answer.value = announced_level
            answer.save()
        level, created = ChildActivityLevel.objects.get_or_create(
            activity=registration.course.activity, child=registration.child
        )
        if created:
            print(("Created level for child {}".format(registration.child)))
            if old_level:
                converted_level = old_level.split(" ")[-1].upper()
                if level.before_level != converted_level:
                    print("update level")
                    level.before_level = converted_level
                    level.save()
"""
hiver 2022:

Colonnes:
ID LAGAPEO	Id Favre	RéférenceCours	SSF 21	niveau	NoCar	dossard
142806	242	250 - SKI  Les Mosses 3-6	A 2B	Débutant	1	69

"""
from __future__ import absolute_import, print_function

import six
from activities.models import ExtraNeed

from import_export.formats.base_formats import XLSX
from registrations.models import ChildActivityLevel, ExtraInfo, Registration, Transport


fmt = XLSX()
f = open("/home/greg/temp/montreux-hiver-2022.xlsx", fmt.get_read_mode())
dataset = fmt.create_dataset(f.read())

level_extra_key = "Niveau de ski/snowboard"
question = ExtraNeed.objects.get(question_label=level_extra_key)

for (
    id_lagapeo,
    registration_id,
    course_name,
    old_level,
    announced_level,
    transport_name,
    bib_number,
) in dataset:
    try:
        registration = Registration.objects.get(pk=registration_id)
    except Registration.DoesNotExist:
        print(("Missing registration: {}".format(registration_id)))
        continue
    if six.text_type(registration.child.id_lagapeo) != id_lagapeo:
        print(("id_lagapeo coherence: {}/{}".format(registration.child.id_lagapeo, id_lagapeo)))
        continue
    if False and transport_name:
        transport, created = Transport.objects.get_or_create(name=transport_name)
        if created:
            print(("Created transport {}".format(transport_name)))
        registration.transport = transport
        registration.save()
    if False and bib_number:
        registration.child.bib_number = bib_number
        registration.child.save()
    if announced_level:
        try:
            answer = registration.extra_infos.get(key=question)
        except:
            answer = ExtraInfo.objects.create(key=question, registration=registration)
        if answer.value != announced_level:
            answer.value = announced_level
            answer.save()

    level, created = ChildActivityLevel.objects.get_or_create(
        activity=registration.course.activity, child=registration.child
    )
    if created:
        print(("Created level for child {}".format(registration.child)))
        if old_level:
            converted_level = old_level.split(" ")[-1].upper()
            if level.before_level != converted_level:
                print("update level")
                level.before_level = converted_level
                level.save()


"""
hiver 2021: Ils ont corrigé le num ssf à la main. Le niveau est à modifier sur le site (pas de matching entre ce que
les parents ont entré et les valeurs possibles du fichier xls.

Colonnes:
Id Favre	niveau -1	NoCar	dossard	niveau
258		    A NP        3	    301	    Non-pratiquant

"""
from activities.models import ExtraNeed
from import_export.formats.base_formats import XLSX
from registrations.models import ChildActivityLevel, ExtraInfo, Registration, Transport


fmt = XLSX()
f = open("/home/greg/temp/montreux-hiver-2021.xlsx", fmt.get_read_mode())
dataset = fmt.create_dataset(f.read())

level_extra_key = "Niveau de ski/snowboard"
question = ExtraNeed.objects.get(question_label=level_extra_key)

for (registration_id, old_level, transport_name, bib_number, announced_level) in dataset:
    try:
        registration = Registration.objects.get(pk=registration_id)
    except Registration.DoesNotExist:
        print(("Missing registration: {}".format(registration_id)))
        continue
    if transport_name:
        transport, created = Transport.objects.get_or_create(name=transport_name)
        if created:
            print(("Created transport {}".format(transport_name)))
        registration.transport = transport
        registration.save()
    if bib_number:
        registration.child.bib_number = bib_number
        registration.child.save()
    if announced_level:
        try:
            answer = registration.extra_infos.get(key=question)
        except:
            answer = ExtraInfo.objects.create(key=question, registration=registration)
        if answer.value != announced_level:
            answer.value = announced_level
            answer.save()

    level, created = ChildActivityLevel.objects.get_or_create(
        activity=registration.course.activity, child=registration.child
    )
    if created:
        print(("Created level for child {}".format(registration.child)))
        if old_level:
            converted_level = old_level.split(" ")[-1].upper()
            if level.before_level != converted_level:
                print("update level")
                level.before_level = converted_level
                level.save()


"""
Afin que je puisse confirmer l'inscription aux parents, peux tu stp importer les informations qui se trouvent sur le
fichier excel en annexe dès que possible?

Colonnes:
Id Favre    num. ssf    NoCar    dossard    niveau                  SSF 18
100	        96657       6        519        Moyen (niveau 4 à 6)    A 4B

"""
from activities.models import ExtraNeed
from import_export.formats.base_formats import XLSX
from registrations.models import ChildActivityLevel, ExtraInfo, Registration, Transport


fmt = XLSX()
f = open("/home/grfavre/montreux-hiver-2020.xlsx", fmt.get_read_mode())
dataset = fmt.create_dataset(f.read())

level_extra_key = "Niveau de ski/snowboard"
question = ExtraNeed.objects.get(question_label=level_extra_key)

for (
    registration_id,
    id_lagapeo,
    last_name,
    first_name,
    announced_level,
    old_level,
    transport_name,
    bib_number,
) in dataset:
    try:
        registration = Registration.objects.get(pk=registration_id)
    except Registration.DoesNotExist:
        print(("Missing registration: {}".format(registration_id)))
        continue
    if six.text_type(registration.child.id_lagapeo) != id_lagapeo:
        print(("id_lagapeo coherence: {}/{}".format(registration.child.id_lagapeo, id_lagapeo)))
        continue
    if transport_name:
        transport, created = Transport.objects.get_or_create(name=transport_name)
        if created:
            print(("Created transport {}".format(transport_name)))
        registration.transport = transport
        registration.save()
    if bib_number:
        registration.child.bib_number = bib_number
        registration.child.save()
    if announced_level:
        try:
            answer = registration.extra_infos.get(key=question)
        except:
            answer = ExtraInfo.objects.create(key=question, registration=registration)
        if answer.value != announced_level:
            answer.value = announced_level
            answer.save()

    level, created = ChildActivityLevel.objects.get_or_create(
        activity=registration.course.activity, child=registration.child
    )
    if created:
        print(("Created level for child {}".format(registration.child)))
        if old_level:
            converted_level = old_level.split(" ")[-1].upper()
            if level.before_level != converted_level:
                print("update level")
                level.before_level = converted_level
                level.save()

for (
    registration_id,
    id_lagapeo,
    transport_name,
    bib_number,
    announced_level,
    old_level,
) in dataset:
    try:
        registration = Registration.objects.get(pk=registration_id)
    except Registration.DoesNotExist:
        print(("Missing registration: {}".format(registration_id)))
    if announced_level:
        try:
            answer = registration.extra_infos.get(key=question)
        except:
            answer = ExtraInfo.objects.create(key=question, registration=registration)
        if answer.value != announced_level:
            answer.value = announced_level
            answer.save()

    level, created = ChildActivityLevel.objects.get_or_create(
        activity=registration.course.activity, child=registration.child
    )
    if created:
        print(("Created level for child {}".format(registration.child)))
    if old_level:
        converted_level = old_level.split(" ")[-1].upper()
        if level.before_level != converted_level:
            print("update level")
            level.before_level = converted_level
            level.save()

## reload_levels
for (
    registration_id,
    id_lagapeo,
    last_name,
    first_name,
    announced_level,
    old_level,
    transport_name,
    bib_number,
) in dataset:
    try:
        registration = Registration.objects.get(pk=registration_id)
    except Registration.DoesNotExist:
        print(("Missing registration: {}".format(registration_id)))
        continue
    if six.text_type(registration.child.id_lagapeo) != id_lagapeo:
        print(("id_lagapeo coherence: {}/{}".format(registration.child.id_lagapeo, id_lagapeo)))
        continue
    level, created = ChildActivityLevel.objects.get_or_create(
        activity=registration.course.activity, child=registration.child
    )
    if old_level:
        if level.before_level != old_level:
            print("update level")
            level.before_level = old_level
            level.save()
