from absences.models import Absence
from activities.models import Course
from registrations.models import Registration


for course in Course.objects.all().prefetch_related("sessions", "participants", "participants__child"):
    print(f"course: {course}")
    for registration in course.participants.all():
        for session in course.sessions.all():
            print(f"session: {session}")
            Absence.objects.get_or_create(
                child=registration.child,
                session=session,
                defaults={"status": Absence.STATUS.present},
            )


# Check coherence, and cleanup

for course in Course.objects.all().prefetch_related("sessions", "participants", "participants__child"):
    # print(f"course: {course}")
    for session in course.sessions.all():
        if session.absences.count() > course.participants.count():
            print(f"session: {session}")
            session.absences.exclude(child__in=course.participants.values_list("child", flat=True)).delete()


for reg in Registration.objects.all_with_deleted().filter(status="canceled"):
    absences_of_canceled_registrations = Absence.objects.filter(session__course=reg.course, child=reg.child)

    for absence in absences_of_canceled_registrations:
        if absence.session.date >= reg.modified.date():
            print("will delete %s" % absence)
            # absence.delete()
