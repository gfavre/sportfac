from __future__ import absolute_import, print_function

from dateutil import tz
from registrations.models import Registration


from_zone = tz.gettz("UTC")
to_zone = tz.gettz("Europe/Zurich")

for reg in Registration.objects.select_related("course", "course__activity").order_by("created"):
    print(
        (
            "\t".join(
                (
                    str(reg.created.astimezone(to_zone)),
                    reg.course.activity.name,
                    str(reg.course.number),
                )
            )
        )
    )


course_nb = {}
for reg in Registration.objects.select_related("course", "course__activity").order_by("created"):
    if reg.course not in course_nb:
        course_nb[reg.course] = 1
    else:
        course_nb[reg.course] += 1
    if course_nb[reg.course] == reg.course.max_participants:
        print(
            (
                "\t".join(
                    (
                        str(reg.created.astimezone(to_zone)),
                        reg.course.activity.name,
                        str(reg.course.number),
                        "Cours complet",
                    )
                )
            )
        )
        all_full = True
        for course in reg.course.activity.courses.all():
            all_full &= course_nb.setdefault(course, 0) == course.max_participants
            if not all_full:
                break
        if all_full:
            print(
                (
                    "\t".join(
                        (
                            str(reg.created.astimezone(to_zone)),
                            reg.course.activity.name,
                            str(reg.course.number),
                            "Activité complète",
                        )
                    )
                )
            )

from collections import OrderedDict


hour_minutes = OrderedDict()
for reg in Registration.objects.select_related("course", "course__activity").order_by("created"):
    dt = reg.created.astimezone(to_zone)
    if (dt.hour, dt.minute) not in hour_minutes:
        hour_minutes[(dt.hour, dt.minute)] = 1
    else:
        hour_minutes[(dt.hour, dt.minute)] += 1

for ((hour, minute), nb_events) in hour_minutes.items():
    print(("\t".join(("{}:{}".format(hour, minute), str(nb_events)))))


from activities.models import Activity


for activity in Activity.objects.all():
    total = 0
    for course in activity.courses.all():
        total += course.max_participants
    print(("\t".join((activity.name, str(total)))))
