from decimal import Decimal

from django.conf import settings
from django.utils.timezone import now

from absences.models import Session
from activities.models import CoursesInstructors
from sportfac.utils import ExcelWriter


HOURS_IN_DAY = Decimal("24")
SECONDS_IN_HOUR = Decimal("3600")


def get_payroll_csv(payroll_obj, filelike):
    qs_kwargs = {"date__gte": payroll_obj.start, "date__lte": payroll_obj.end}
    if not payroll_obj.include_already_exported:
        qs_kwargs["export_date__isnull"] = True
    sessions = Session.objects.filter(**qs_kwargs).values_list("course", "instructor")
    count = {}
    for course_id, instructor_id in sessions:
        count[(course_id, instructor_id)] = count.get((course_id, instructor_id), 0) + 1
    writer = ExcelWriter(
        filelike,
    )
    if payroll_obj.add_details:
        heading = [
            "Identifiant moniteur",
            "Code de fonction",
            "Numéro de contrat",
            "Nombre d'heures",
            "Date de début",
            "Date de fin",
            "Moniteur",
            "Activité",
            "Cours",
            "Durée",
            "Fonction",
            "Tarif horaire",
            "Effectif moyen",
        ]
        writer.writerow(heading)
    for course_instructor in CoursesInstructors.objects.all():
        if (course_instructor.course_id, course_instructor.instructor_id) not in count:
            continue
        if not course_instructor.instructor.external_identifier:
            continue
        if not course_instructor.function:
            continue
        nb_rate = count[(course_instructor.course_id, course_instructor.instructor_id)]
        course_instructor.exported_count = nb_rate
        if course_instructor.function.is_hourly:
            duration = course_instructor.course.duration
            hours_days = Decimal(duration.days) * HOURS_IN_DAY
            hours_seconds = Decimal(duration.seconds) / SECONDS_IN_HOUR
            nb_hours = (hours_days + hours_seconds) * Decimal(course_instructor.exported_count)
            nb_hours = nb_hours.quantize(Decimal("0.00"))
        elif course_instructor.function.is_daily:
            nb_hours = course_instructor.exported_count
        else:
            nb_hours = course_instructor.exported_count

        line = [
            course_instructor.instructor.external_identifier,
            course_instructor.function.code,
            str(course_instructor.contract_number),
            round(nb_hours, 2),
            payroll_obj.start.strftime(settings.SWISS_DATE_SHORT),
            payroll_obj.end.strftime(settings.SWISS_DATE_SHORT),
        ]
        if payroll_obj.add_details:
            course_sessions = course_instructor.course.sessions.filter(**qs_kwargs)
            total_presentees = sum([session.presentees_nb() for session in course_sessions])
            nb_sessions = course_sessions.count()
            avg_presentees = round(float(total_presentees) / max(nb_sessions, 1), 1)

            line += [
                course_instructor.instructor.full_name,
                course_instructor.course.activity.name,
                course_instructor.course.number,
                course_instructor.course.duration,
                course_instructor.function.name,
                course_instructor.function.rate,
                avg_presentees,
            ]
        writer.writerow(line)
    if payroll_obj.set_as_exported:
        Session.objects.filter(**qs_kwargs).update(export_date=now())
