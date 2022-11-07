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
                continue

from datetime import date
dates = [date(2021,1,9), date(2021,1,16)]
for registration in Registration.objects.all():
    for session in registration.course.sessions.filter(date__gte=now()):
        Absence.objects.get_or_create(
            child=self.child, session=future_session,
            defaults={'status': Absence.STATUS.present}
        )
    registration.create_future_absences()

for registration in
dates = [date(2021,1,9), date(2021,1,16)]


#for absence in Absence.objects.all():
#    if absence.session.course not in absence.child.courses.all():
#        absence.delete()
