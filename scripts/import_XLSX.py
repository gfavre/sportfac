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


from import_export.formats.base_formats import XLSX
from registrations.models import Child, Registration

fmt = XLSX()
f = open('/home/grfavre/niveau-1.xlsx', fmt.get_read_mode())
dataset = fmt.create_dataset(f.read())
for (registration_id, first, level_before) in dataset:
    if not level_before:
        continue
    try:
        registration = Registration.objects.get(pk=registration_id)
        assert (registration.child.first_name == first)
        lvl = level_before[-2:]
        if lvl in Registration.LEVELS:
            registration.before_level = lvl
            print('New level: %s' % lvl)
            registration.save()
    except Registration.DoesNotExist:
        print('NO registration found')
        continue


from import_export.formats.base_formats import XLSX
from registrations.models import Child, Registration, ChildActivityLevel

fmt = XLSX()
f = open('/home/grfavre/SSF_Hiver_Inscription.xlsx', fmt.get_read_mode())
#f = open('/Users/grfavre/Desktop/SSF_Hiver_Inscription.xlsx', fmt.get_read_mode())
dataset = fmt.create_dataset(f.read())
all_ids = set(Child.objects.values_list('id_lagapeo', flat=True))
for (junk, registration_id, a_name, c_name, price, first, last, id_lagapeo, bdate, s_year, s_name, emergency,
     p_first, p_last, email, address, npa, city, country, level, train, abo_annonce, abo) in dataset:
    if not registration_id:
        continue
    try:
        registration = Registration.objects.get(pk=registration_id)
        assert (registration.child.first_name == first)
        child = registration.child
        if not child.id_lagapeo and id_lagapeo and id_lagapeo in all_ids:
            child2 = Child.objects.get(id_lagapeo=id_lagapeo)
            if child2.registrations.exists():
                print("dual registered child: {}".format(id_lagapeo))
                continue
            child2.delete()
        child.id_lagapeo = id_lagapeo
        child.save()
        for extra in registration.extra_infos.all():
            if extra.key.question_label == u'Niveau de ski/snowboard':
                if extra.value != level:
                    print(u'{} ≠ {}'.format(extra.value, level))
                    extra.value = level or ''
                    extra.save()
            elif extra.key.question_label == u'Arrêt de Bus':
                if extra.value != train:
                    print(u'{} ≠ {}'.format(extra.value, train))
                    extra.value = train or ''
                    extra.save()
            elif extra.key.question_label == u'Votre enfant aura-t-il un abonnement de ski saison?':
                if extra.value != abo_annonce:
                    print(u'{} ≠ {}'.format(extra.value, abo_annonce))
            elif extra.key.question_label == u'Arrêt de train':
                if extra.value != train:
                    print(u'{} ≠ {}'.format(extra.value, train))
                    extra.value = train or ''
                    extra.save()
            elif extra.key.question_label == u'Snowboard ou ski?':
                pass
    except AssertionError:
        print('Bad name: {} != {} {}'.format(registration.child.full_name, first, last))
        continue
    except Registration.DoesNotExist:
        print('NO registration found: {}'.format(registration_id))
        continue


from import_export.formats.base_formats import XLSX
from registrations.models import Child, Registration, ChildActivityLevel, Transport

fmt = XLSX()
f = open('/home/grfavre/Valeurs cars, dossard et autres au 14.12.17.xlsx', fmt.get_read_mode())
#f = open('/Users/grfavre/Desktop/Valeurs cars, dossard et autres au 14.12.17.xlsx', fmt.get_read_mode())
dataset = fmt.create_dataset(f.read())
cars = {}

for (registration_id, c_first, c_last, car, junk, junk, bib_number, junk, id_lagapeo, junk, c_name, level_before) in dataset:
    try:
        registration = Registration.objects.get(pk=registration_id)
        if not car in cars:
            car_obj, created = Transport.objects.get_or_create(name=car)
            cars[car] = car_obj
        else:
            car_obj = cars[car]
        registration.transport = car_obj
        child = registration.child
        if bib_number:
            child.bib_number = bib_number
            child.save()
        if level_before:
            level_before = level_before.split(' ')[-1]
            lvl, created = ChildActivityLevel.objects.get_or_create(
                activity=registration.course.activity,
                child=child,
                defaults={'before_level': level_before})
            lvl.save()
        registration.save()
    except Registration.DoesNotExist:
        print('NO registration found: {}'.format(registration_id))
        continue
