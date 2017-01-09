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



from profiles.models import FamilyUser
from import_export.formats.base_formats import XLSX

from backend.templatetags.switzerland import ahv

fmt = XLSX()
f = open('/home/grfavre/moniteurs2017.xlsx', fmt.get_read_mode())
dataset = fmt.create_dataset(f.read())
for (email, last_name, first_name, phone, zipcode, city, birth_date, ahv_val) in dataset:
    zipcode = str(zipcode)
    if ahv_val:
        ahv_val = ahv(str(ahv_val))
    else:
        ahv_val = ''
    supervisor, created = FamilyUser.objects.get_or_create(
                            email=email,
                            defaults={'first_name': first_name,
                                      'last_name': last_name,
                                      'private_phone2': phone,
                                      'zipcode': zipcode,
                                      'birth_date': birth_date,
                                      'city': city,
                                      'ahv': ahv_val})
    if created:
        supervisor.set_password('montreux')
    supervisor.is_instructor = True
    supervisor.save()