from decimal import Decimal
from django.conf import settings
from django.utils.timezone import now

from absences.models import Session
from activities.models import CoursesInstructors, RATE_MODES

from sportfac.utils import ExcelWriter


def get_payroll_csv(payroll_obj, filelike):
    qs_kwargs = {'date__gte': payroll_obj.start, 'date__lte': payroll_obj.end}
    if not payroll_obj.include_already_exported:
        qs_kwargs['export_date__isnull'] = True
    sessions = Session.objects.filter(**qs_kwargs).values_list('course', 'instructor')
    count = {}
    for (course_id, instructor_id) in sessions:
        count[(course_id, instructor_id)] = count.get((course_id, instructor_id), 0) + 1

    writer = ExcelWriter(filelike, )
    for course_instructor in CoursesInstructors.objects.all():
        if not (course_instructor.course_id, course_instructor.instructor_id) in count:
            continue
        if not course_instructor.instructor.external_identifier:
            continue
        if not course_instructor.function:
            continue
        nb_rate = count[(course_instructor.course_id, course_instructor.instructor_id)]
        course_instructor.exported_count = nb_rate
        if course_instructor.function.rate_mode == RATE_MODES.hour:
            duration = course_instructor.course.duration
            nb_hours = Decimal(duration.seconds / 3600.0 + duration.days * 24) * course_instructor.exported_count
        elif course_instructor.function.rate_mode == RATE_MODES.day:
            nb_hours = course_instructor.exported_count
        else:
            nb_hours = course_instructor.exported_count

        line = [
            course_instructor.instructor.external_identifier,
            course_instructor.function.code,
            str(nb_hours),
            payroll_obj.start.strftime(settings.SWISS_DATE_SHORT),
            payroll_obj.end.strftime(settings.SWISS_DATE_SHORT)
        ]
        if payroll_obj.add_details:
            line += [
                course_instructor.instructor.full_name,
                course_instructor.function.name,
            ]
        writer.writerow(line)
    if payroll_obj.set_as_exported:
        Session.objects.filter(**qs_kwargs).update(export_date=now())
