from registrations.models import Registration

r = Registration.objects.filter(child__first_name="Naïla", course__number="EN/04-2023").last()
r.create_future_absences()