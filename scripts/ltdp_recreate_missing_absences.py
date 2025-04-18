from django.utils.timezone import now

from registrations.models import Registration


for r in Registration.objects.all():
    future_courses = r.course.sessions.filter(date__gte=now()).count()
    future_absences = r.child.absence_set.filter(session__date__gte=now(), session__course=r.course).count()
    if future_courses != future_absences:
        print(r.child, r.course, future_courses, future_absences)
        # r.create_future_absences()

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

r = Registration.objects.get(child__first_name="Luciana", course__number="EN/03-2023")
r.create_future_absences()

r = Registration.objects.get(child__first_name="Enzo Raphael", course__number="EN/02-2023")
r.create_future_absences()
