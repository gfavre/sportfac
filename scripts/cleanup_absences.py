# -*- coding: utf-8 -*-
from activities.models import Course
from absences.models import Absence

for course in Course.objects.filter(visible=True).prefetch_related('sessions', 'participants', 'participants__child'):
    print(u'course: {}'.format(course))
    for registration in course.participants.all():
        for session in course.sessions.all():
            print(u'session: {}'.format(session))
            Absence.objects.get_or_create(
                child=registration.child, session=session,
                defaults={
                            'status': Absence.STATUS.present
                }
            )
