from import_export.formats.base_formats import XLSX

from registrations.models import Child, Registration

fmt = XLSX()
f = open('/home/grfavre/montreux.xlsx', fmt.get_read_mode())
dataset = fmt.create_dataset(f.read())

for (registration_id, id_lagapeo, bib_number, transport_info, last, first) in dataset:
    try:
        registration = Registration.objects.get(pk=registration_id)
        assert(registration.child.first_name == first)
        assert(registration.child.last_name == last)
        child = registration.child
        child.id_lagapeo = id_lagapeo
        child.bib_number = bib_number
        try:
            child.save()
        except:
            c2 = Child.objects.get(id_lagapeo=id_lagapeo, family=None)
            c2.delete()
            child.save()
        print (u'Child {} updated'.format(child.full_name))
        registration.transport_info = transport_info
        registration.save()
    except Registration.DoesNotExist:
        print('NO registration found')
        continue