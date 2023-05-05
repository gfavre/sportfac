from registrations.models import Registration

r = Registration.objects.get(child__first_name__startswith="Sidney", course__number="EN/01-2023")
r.create_future_absences()

r = Registration.objects.get(child__first_name="Mahmud", course__number="EN/01-2023")
r.create_future_absences()

r = Registration.objects.get(child__first_name="Lucas", course__number="EN/02-2-2023")
r.create_future_absences()

r = Registration.objects.get(child__first_name="Thierry", course__number="EN/02-2-2023")
r.create_future_absences()

r = Registration.objects.get(child__first_name="Léon", course__number="EN/04-2023")
r.create_future_absences()
r = Registration.objects.get(child__first_name__startswith="JOLANTA", course__number="EN/04-2023")
r.create_future_absences()

r = Registration.objects.get(child__first_name="Rui Filipe", course__number="EN/04-2023")
r.create_future_absences()

r = Registration.objects.get(child__first_name="Mael", course__number="EN/04-2023")
r.create_future_absences()

r = Registration.objects.get(child__first_name="Numa", course__number="EN/04-2023")
r.create_future_absences()
