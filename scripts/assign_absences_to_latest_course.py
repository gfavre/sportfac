# -*- coding: utf-8 -*-
import datetime
from activities.models import Course

from absences.models import Session, Absence
from registrations.models import Registration
from registrations.models import Child

courses = ['200.01', '200.02', '200.03', '200.04', '200.05', '200.06', '200.07', '200.08', '200.09', '200.10', '200.11',
           '210.01', '210.02', '210.03', '210.04', '210.05', '210.06',
           '220.01', '220.02', '220.03']
main_courses = Course.objects.filter(number__in=['200 - SKI : R-d-N 3-6', '210 - SKI : R-d-N 7-12', '220 - SNOW : R-d-N'])
for course in Course.objects.all():
    if not course.number[:6] in courses:
        continue
    sessions = {session.date: session for session in course.sessions.all()}
    for registration in course.participants.all():
        child = registration.child
        for absence in child.absence_set.all():
            absence.session = sessions[absence.session.date]
            try:
                absence.save()
            except:
                import pdb;pdb.set_trace()
                continue