import pandas as pd
from import_export.formats.base_formats import XLSX

from activities.models import ExtraNeed
from registrations.models import Child
from registrations.models import ChildActivityLevel
from registrations.models import ExtraInfo
from registrations.models import Registration
from registrations.models import Transport


################################
# hiver 2026 - part 2 - dossards
# id	Cours	Prénom	Nom	AVS	Identifiant de l'enfant	Arrêt de bus	Base_niveaux.N°car	Base_niveaux.N° Dossard

file_path = "/home/greg/temp/20251207_Dossards_transports.xlsx"
file_path = "/home/greg/temp/Inscriptions Les Mosses 2026.xlsx"
data = pd.read_excel(file_path)
for _index, row in data.iterrows():
    registration_id = row["id"]
    try:
        registration = Registration.objects.get(pk=registration_id)
    except Registration.DoesNotExist:
        print(f"Missing registration: {registration_id}")
        continue
    bib_number = str(row["Base_niveaux.N° Dossard"]) if pd.notna(row["Base_niveaux.N° Dossard"]) else ""
    first_name = row["Prénom"]
    if first_name != registration.child.first_name:
        print(f"child mismatch first name: {first_name} / registration_child_name: {registration.child.first_name}")
        continue
    registration.child.bib_number = bib_number
    registration.child.save(update_fields=["bib_number"])
    transport_name = str(row["Base_niveaux.N°car"]) if pd.notna(row["Base_niveaux.N°car"]) else ""
    if transport_name:
        transport, created = Transport.objects.get_or_create(name=transport_name)
        if created:
            print(f"Created transport {transport_name}")
        registration.transport = transport
        registration.save(update_fields=["transport"])
    old_level = str(row["Niveau avant le cours"]) if pd.notna(row["Niveau avant le cours"]) else ""
    if old_level:
        level, created = ChildActivityLevel.objects.get_or_create(
            activity=registration.course.activity, child=registration.child
        )
        if old_level.startswith("A ") or old_level.startswith("S "):
            old_level = " ".join(old_level.split(" ")[1:])
        level.before_level = old_level
        level.save(update_fields=["before_level"])

# Hiver 2026, partie 1:
# id	Prénom	Nom	Identifiant de l'enfant	Date de naissance	Niveau après le cours
# id c'est pas registration_id!! je sais pas doû ça vient => id de l'0année passée!!!! wtf!
file_path = "/home/greg/temp/montreux-hiver-2026.xlsx"
data = pd.read_excel(file_path)
level_extra_key = "Niveau de ski/snowboard"
question = ExtraNeed.objects.get(question_label=level_extra_key)

for _index, row in data.iterrows():
    # registration_id = row["id"]
    id_lagapeo = str(row["Identifiant de l'enfant"]) if pd.notna(row["Identifiant de l'enfant"]) else ""
    bib_number = str(int(row["Dossards"])) if row.get("Dossards") and pd.notna(row["Dossards"]) else ""
    transport_name = str(int(row["Transport"])) if row.get("Transport") and pd.notna(row["Transport"]) else ""
    old_level = str(row["Niveau après le cours"]) if pd.notna(row["Niveau après le cours"]) else ""
    announced_level = (
        str(row["Niveau annoncé"]) if row.get("Niveau annoncé") and pd.notna(row["Niveau annoncé"]) else ""
    )

    try:
        child = Child.objects.get(id_lagapeo=id_lagapeo)
        registrations = child.registrations.all()
        if not registrations.exists():
            print("child has no registrations, skipping")
            continue
        assert registrations.count() == 1
        registration = child.registrations.first()
        # registration = Registration.objects.get(pk=registration_id)
    except Child.DoesNotExist:
        print(f"Missing Child: {id_lagapeo}, {row['Prénom']} {row['Nom']}")
        continue
    if str(registration.child.id_lagapeo) != id_lagapeo:
        print(f"id_lagapeo coherence: {registration.child.id_lagapeo}/{id_lagapeo}")
        continue

    if transport_name:
        transport, created = Transport.objects.get_or_create(name=transport_name)
        if created:
            print(f"Created transport {transport_name}")
        registration.transport = transport
        registration.save()
    if pd.notna(bib_number):
        registration.child.bib_number = bib_number
        registration.child.save()
    if pd.notna(announced_level):
        try:
            answer = registration.extra_infos.get(key=question)
        except ExtraInfo.DoesNotExist:
            answer = ExtraInfo.objects.create(key=question, registration=registration)
        if answer.value != announced_level:
            answer.value = announced_level
            answer.save()
    if pd.notna(old_level):
        try:
            answer = registration.extra_infos.get(key=question)
        except ExtraInfo.DoesNotExist:
            answer = ExtraInfo.objects.create(key=question, registration=registration)
        if answer.value != announced_level:
            answer.value = announced_level
            answer.save()
        level, created = ChildActivityLevel.objects.update_or_create(
            activity=registration.course.activity, child=registration.child, defaults={"before_level": old_level}
        )


# """
# hiver 2025:
# id	Activité	Cours	Prénom	Nom	Identifiant de l'enfant	Date de naissance	Année scolaire	École
# Numéro d'urgence	E-mail	Arrêt de train	Arrêt de bus	Dossards	Transport	Niveau avant le cours 2025
# Niveau annoncé
file_path = "/home/greg/temp/montreux-hiver-2025.xlsx"
data = pd.read_excel(file_path)
level_extra_key = "Niveau de ski/snowboard"
question = ExtraNeed.objects.get(question_label=level_extra_key)

for _index, row in data.iterrows():
    registration_id = row["id"]
    id_lagapeo = str(row["Identifiant de l'enfant"]) if pd.notna(row["Identifiant de l'enfant"]) else ""
    bib_number = str(int(row["Dossards"])) if pd.notna(row["Dossards"]) else ""
    transport_name = str(int(row["Transport"])) if pd.notna(row["Transport"]) else ""
    old_level = str(row["Niveau avant le cours 2025"]) if pd.notna(row["Niveau avant le cours 2025"]) else ""
    announced_level = str(row["Niveau annoncé"]) if pd.notna(row["Niveau annoncé"]) else ""
    try:
        registration = Registration.objects.get(pk=registration_id)
    except Registration.DoesNotExist:
        print(f"Missing registration: {registration_id}")
        continue
    if str(registration.child.id_lagapeo) != id_lagapeo:
        print(f"id_lagapeo coherence: {registration.child.id_lagapeo}/{id_lagapeo}")
        continue
    if transport_name:
        transport, created = Transport.objects.get_or_create(name=transport_name)
        if created:
            print(f"Created transport {transport_name}")
        registration.transport = transport
        registration.save()
    if pd.notna(bib_number):
        registration.child.bib_number = bib_number
        registration.child.save()
    if pd.notna(announced_level):
        try:
            answer = registration.extra_infos.get(key=question)
        except ExtraInfo.DoesNotExist:
            answer = ExtraInfo.objects.create(key=question, registration=registration)
        if answer.value != announced_level:
            answer.value = announced_level
            answer.save()
        level, created = ChildActivityLevel.objects.get_or_create(
            activity=registration.course.activity, child=registration.child
        )
        if created:
            print(f"Created level for child {registration.child}")
            if pd.notna(old_level):
                if old_level.startswith("A ") or old_level.startswith("S "):
                    old_level = " ".join(old_level.split(" ")[1:])
                if level.before_level != old_level:
                    print("update level")
                    level.before_level = old_level
                    level.save()

# """
# hiver 2024
# Id Favre	ID LAGAPEO	Nom	Prénom	dossard	niveau	NoCar	Embarquement	niveau avant le cours
# 6	259123	Imbert-Vier	Jade	15	Moyen	1	2 Clarens Vinet Nord	A A 5A
# """
fmt = XLSX()
with open("/home/greg/temp/montreux-hiver-2024.xlsx", fmt.get_read_mode()) as f:
    dataset = fmt.create_dataset(f.read())
level_extra_key = "Niveau de ski/snowboard"
question = ExtraNeed.objects.get(question_label=level_extra_key)
for (
    registration_id,
    id_lagapeo,
    _first_name,
    _last_name,
    bib_number,
    announced_level,
    transport_name,
    _transport_place,
    old_level,
) in dataset:
    try:
        registration = Registration.objects.get(pk=registration_id)
    except Registration.DoesNotExist:
        print(f"Missing registration: {registration_id}")
        continue
    if str(registration.child.id_lagapeo) != id_lagapeo:
        print(f"id_lagapeo coherence: {registration.child.id_lagapeo}/{id_lagapeo}")
        continue
    if transport_name:
        transport, created = Transport.objects.get_or_create(name=transport_name)
        if created:
            print(f"Created transport {transport_name}")
        registration.transport = transport
        registration.save()
    if bib_number:
        registration.child.bib_number = bib_number
        registration.child.save()
    if announced_level:
        try:
            answer = registration.extra_infos.get(key=question)
        except ExtraInfo.DoesNotExist:
            answer = ExtraInfo.objects.create(key=question, registration=registration)
        if answer.value != announced_level:
            answer.value = announced_level
            answer.save()
        level, created = ChildActivityLevel.objects.get_or_create(
            activity=registration.course.activity, child=registration.child
        )
        if created:
            print(f"Created level for child {registration.child}")
            if old_level:
                if old_level.startswith("A ") or old_level.startswith("S "):
                    old_level = " ".join(old_level.split(" ")[1:])
                if level.before_level != old_level:
                    print("update level")
                    level.before_level = old_level
                    level.save()


# """
# hiver 2023:
#
# Colonnes:
# Id Favre	ID LAGAPEO	Nom	Prénom	dossard	NoCar	SSF 22	niveau
# 3	323386	Grandvuinet	Ilyas	413	4	S 5B	Moyen
# """

fmt = XLSX()
f = open("/home/greg/temp/montreux-hiver-2023.xlsx", fmt.get_read_mode())
dataset = fmt.create_dataset(f.read())
level_extra_key = "Niveau de ski/snowboard"
question = ExtraNeed.objects.get(question_label=level_extra_key)

for (
    registration_id,
    id_lagapeo,
    _first_name,
    _last_name,
    bib_number,
    transport_name,
    old_level,
    announced_level,
) in dataset:
    try:
        registration = Registration.objects.get(pk=registration_id)
    except Registration.DoesNotExist:
        print(f"Missing registration: {registration_id}")
        continue
    if str(registration.child.id_lagapeo) != id_lagapeo:
        print(f"id_lagapeo coherence: {registration.child.id_lagapeo}/{id_lagapeo}")
        continue
    if transport_name:
        transport, created = Transport.objects.get_or_create(name=transport_name)
        if created:
            print(f"Created transport {transport_name}")
        registration.transport = transport
        registration.save()
    if bib_number:
        registration.child.bib_number = bib_number
        registration.child.save()
    if announced_level:
        try:
            answer = registration.extra_infos.get(key=question)
        except ExtraInfo.DoesNotExist:
            answer = ExtraInfo.objects.create(key=question, registration=registration)
        if answer.value != announced_level:
            answer.value = announced_level
            answer.save()
        level, created = ChildActivityLevel.objects.get_or_create(
            activity=registration.course.activity, child=registration.child
        )
        if created:
            print(f"Created level for child {registration.child}")
            if old_level:
                converted_level = old_level.split(" ")[-1].upper()
                if level.before_level != converted_level:
                    print("update level")
                    level.before_level = converted_level
                    level.save()
# """
# hiver 2022:
#
# Colonnes:
# ID LAGAPEO	Id Favre	RéférenceCours	SSF 21	niveau	NoCar	dossard
# 142806	242	250 - SKI  Les Mosses 3-6	A 2B	Débutant	1	69
#
# """

fmt = XLSX()
f = open("/home/greg/temp/montreux-hiver-2022.xlsx", fmt.get_read_mode())
dataset = fmt.create_dataset(f.read())

level_extra_key = "Niveau de ski/snowboard"
question = ExtraNeed.objects.get(question_label=level_extra_key)

for (
    id_lagapeo,
    registration_id,
    _course_name,
    old_level,
    announced_level,
    transport_name,
    bib_number,
) in dataset:
    try:
        registration = Registration.objects.get(pk=registration_id)
    except Registration.DoesNotExist:
        print(f"Missing registration: {registration_id}")
        continue
    if str(registration.child.id_lagapeo) != id_lagapeo:
        print(f"id_lagapeo coherence: {registration.child.id_lagapeo}/{id_lagapeo}")
        continue
    if False and transport_name:
        transport, created = Transport.objects.get_or_create(name=transport_name)
        if created:
            print(f"Created transport {transport_name}")
        registration.transport = transport
        registration.save()
    if False and bib_number:
        registration.child.bib_number = bib_number
        registration.child.save()
    if announced_level:
        try:
            answer = registration.extra_infos.get(key=question)
        except ExtraInfo.DoesNotExist:
            answer = ExtraInfo.objects.create(key=question, registration=registration)
        if answer.value != announced_level:
            answer.value = announced_level
            answer.save()

    level, created = ChildActivityLevel.objects.get_or_create(
        activity=registration.course.activity, child=registration.child
    )
    if created:
        print(f"Created level for child {registration.child}")
        if old_level:
            converted_level = old_level.split(" ")[-1].upper()
            if level.before_level != converted_level:
                print("update level")
                level.before_level = converted_level
                level.save()


# """
# hiver 2021: Ils ont corrigé le num ssf à la main. Le niveau est à modifier sur le site (pas de matching entre ce que
# les parents ont entré et les valeurs possibles du fichier xls.
#
# Colonnes:
# Id Favre	niveau -1	NoCar	dossard	niveau
# 258		    A NP        3	    301	    Non-pratiquant
#
# """


fmt = XLSX()
f = open("/home/greg/temp/montreux-hiver-2021.xlsx", fmt.get_read_mode())
dataset = fmt.create_dataset(f.read())

level_extra_key = "Niveau de ski/snowboard"
question = ExtraNeed.objects.get(question_label=level_extra_key)

for registration_id, old_level, transport_name, bib_number, announced_level in dataset:
    try:
        registration = Registration.objects.get(pk=registration_id)
    except Registration.DoesNotExist:
        print(f"Missing registration: {registration_id}")
        continue
    if transport_name:
        transport, created = Transport.objects.get_or_create(name=transport_name)
        if created:
            print(f"Created transport {transport_name}")
        registration.transport = transport
        registration.save()
    if bib_number:
        registration.child.bib_number = bib_number
        registration.child.save()
    if announced_level:
        try:
            answer = registration.extra_infos.get(key=question)
        except ExtraInfo.DoesNotExist:
            answer = ExtraInfo.objects.create(key=question, registration=registration)
        if answer.value != announced_level:
            answer.value = announced_level
            answer.save()

    level, created = ChildActivityLevel.objects.get_or_create(
        activity=registration.course.activity, child=registration.child
    )
    if created:
        print(f"Created level for child {registration.child}")
        if old_level:
            converted_level = old_level.split(" ")[-1].upper()
            if level.before_level != converted_level:
                print("update level")
                level.before_level = converted_level
                level.save()


# """
# Afin que je puisse confirmer l'inscription aux parents, peux tu stp importer les informations qui se trouvent sur le
# fichier excel en annexe dès que possible?
#
# Colonnes:
# Id Favre    num. ssf    NoCar    dossard    niveau                  SSF 18
# 100	        96657       6        519        Moyen (niveau 4 à 6)    A 4B
#
# """
fmt = XLSX()
f = open("/home/grfavre/montreux-hiver-2020.xlsx", fmt.get_read_mode())
dataset = fmt.create_dataset(f.read())

level_extra_key = "Niveau de ski/snowboard"
question = ExtraNeed.objects.get(question_label=level_extra_key)

for (
    registration_id,
    id_lagapeo,
    _last_name,
    _first_name,
    announced_level,
    old_level,
    transport_name,
    bib_number,
) in dataset:
    try:
        registration = Registration.objects.get(pk=registration_id)
    except Registration.DoesNotExist:
        print(f"Missing registration: {registration_id}")
        continue
    if str(registration.child.id_lagapeo) != id_lagapeo:
        print(f"id_lagapeo coherence: {registration.child.id_lagapeo}/{id_lagapeo}")
        continue
    if transport_name:
        transport, created = Transport.objects.get_or_create(name=transport_name)
        if created:
            print(f"Created transport {transport_name}")
        registration.transport = transport
        registration.save()
    if bib_number:
        registration.child.bib_number = bib_number
        registration.child.save()
    if announced_level:
        try:
            answer = registration.extra_infos.get(key=question)
        except ExtraInfo.DoesNotExist:
            answer = ExtraInfo.objects.create(key=question, registration=registration)
        if answer.value != announced_level:
            answer.value = announced_level
            answer.save()

    level, created = ChildActivityLevel.objects.get_or_create(
        activity=registration.course.activity, child=registration.child
    )
    if created:
        print(f"Created level for child {registration.child}")
        if old_level:
            converted_level = old_level.split(" ")[-1].upper()
            if level.before_level != converted_level:
                print("update level")
                level.before_level = converted_level
                level.save()

for (
    registration_id,
    _id_lagapeo,
    _transport_name,
    _bib_number,
    announced_level,
    old_level,
) in dataset:
    try:
        registration = Registration.objects.get(pk=registration_id)
    except Registration.DoesNotExist:
        print(f"Missing registration: {registration_id}")
    if announced_level:
        try:
            answer = registration.extra_infos.get(key=question)
        except ExtraInfo.DoesNotExist:
            answer = ExtraInfo.objects.create(key=question, registration=registration)
        if answer.value != announced_level:
            answer.value = announced_level
            answer.save()

    level, created = ChildActivityLevel.objects.get_or_create(
        activity=registration.course.activity, child=registration.child
    )
    if created:
        print(f"Created level for child {registration.child}")
    if old_level:
        converted_level = old_level.split(" ")[-1].upper()
        if level.before_level != converted_level:
            print("update level")
            level.before_level = converted_level
            level.save()

# reload_levels
for (
    registration_id,
    id_lagapeo,
    _last_name,
    _first_name,
    _announced_level,
    old_level,
    _transport_name,
    _bib_number,
) in dataset:
    try:
        registration = Registration.objects.get(pk=registration_id)
    except Registration.DoesNotExist:
        print(f"Missing registration: {registration_id}")
        continue
    if str(registration.child.id_lagapeo) != id_lagapeo:
        print(f"id_lagapeo coherence: {registration.child.id_lagapeo}/{id_lagapeo}")
        continue
    level, created = ChildActivityLevel.objects.get_or_create(
        activity=registration.course.activity, child=registration.child
    )
    if old_level:
        if level.before_level != old_level:
            print("update level")
            level.before_level = old_level
            level.save()
