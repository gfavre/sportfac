# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

from absences.models import Absence
from activities.models import Course


for course in Course.objects.filter(visible=True).prefetch_related(
    "sessions", "participants", "participants__child"
):
    print(("course: {}".format(course)))
    for registration in course.participants.all():
        for session in course.sessions.all():
            print(("session: {}".format(session)))
            Absence.objects.get_or_create(
                child=registration.child,
                session=session,
                defaults={"status": Absence.STATUS.present},
            )
