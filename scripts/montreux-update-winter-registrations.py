"""
Afin que je puisse confirmer l'inscription aux parents, peux tu stp importer les informations qui se trouvent sur le
fichier excel en annexe dès que possible?

Colonnes:
Id Favre    num. ssf    NoCar    dossard    niveau                  SSF 18
100	        96657       6        519        Moyen (niveau 4 à 6)    A 4B

"""
from registrations.models import Transport, Registration, ChildActivityLevel

from import_export.formats.base_formats import XLSX


fmt = XLSX()
f = open('/home/grfavre/montreux-hiver-2019.xlsx', fmt.get_read_mode())
dataset = fmt.create_dataset(f.read())

for (registration_id, id_lagapeo, transport_name, bib_number, level, old_level) in dataset:
    try:
        registration = Registration.objects.get(pk=registration_id)
    except Registration.DoesNotExist:
        print('Missing registration: {}'.format(registration_id))
    if unicode(registration.child.id_lagapeo) != id_lagapeo:
        print('id_lagapeo coherence: {}/{}'.format(registration.child.id_lagapeo, id_lagapeo))
    if transport_name:
        transport, created = Transport.objects.get_or_create(name=transport_name)
        if created:
            print('Created transport {}'.format(transport_name))
        registration.transport = transport
        registration.save()
    if bib_number:
        registration.child.bib_number = bib_number
        registration.child.save()
    level, created = ChildActivityLevel.objects.get_or_create(activity=registration.course.activity,
                                                              child=registration.child)
    if created:
        print('Created level for child {}'.format(registration.child))
    if old_level:
        level.before_level = old_level.split(' ')[-1].upper()
        level.save()
