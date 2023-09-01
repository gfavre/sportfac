from __future__ import absolute_import, print_function

import datetime

from absences.models import Absence, Session
from activities.models import Course
from registrations.models import Child, Registration
from six.moves import input


c = 0
for course in Course.objects.all():
    children = [r.child for r in course.participants.all()]
    for session in course.sessions.filter(date__gte=datetime.date.today()):
        for absence in list(session.absences.all()):
            if absence.child not in children:
                c += 1
                absence.delete()


for registration in Registration.objects.all():
    Absence.objects.filter(
        child=registration.child, session__date__gt=registration.modified
    ).exclude(session__course=registration.course).delete()


fuckers = []
for child in Child.objects.all():
    date_dict = {}
    for absence in child.absence_set.all():
        if absence.session.date in date_dict:
            date_dict[absence.session.date].append(absence)
        else:
            date_dict[absence.session.date] = [absence]
    for dates in date_dict.values():
        if len(dates) > 1:
            fuckers.append((child, date_dict))
            break


for child in Child.objects.prefetch_related("registrations"):
    if not child.registrations.exists():
        continue
    latest_registration = child.registrations.first()
    if not latest_registration.course.number[:3] in ("200",):
        continue
    date_dict = {}
    for absence in child.absence_set.all():
        if absence.session.date in date_dict:
            date_dict[absence.session.date].append(absence)
        else:
            date_dict[absence.session.date] = [absence]
    for dates in date_dict.values():
        if len(dates) > 1:
            to_keep = []
            latest_absence = None
            for absence in dates:
                if absence.session.course == latest_registration.course:
                    to_keep.append(absence)
                    latest_absence = absence
                    continue
                if absence.status != "present":
                    to_keep.append(absence)
                    continue
            if len(to_keep) == 1:
                to_remove = Absence.objects.filter(
                    pk__in=[absence.pk for absence in dates if absence != to_keep[0]]
                )
                to_remove.delete()
                continue
            for count, absence in enumerate(to_keep):
                print(("{} - {} - {}".format(count + 1, absence.modified, absence)))
            chosen_num = input("Choose reason: ")
            if not chosen_num:
                continue
            num = int(chosen_num) - 1
            reason = to_keep[num].status
            latest_absence.status = reason
            latest_absence.save()
            to_remove = Absence.objects.filter(
                pk__in=[absence.pk for absence in dates if absence != latest_absence]
            )
            to_remove.delete()

from datetime import date


for child in Child.objects.prefetch_related("registrations"):
    if not child.registrations.exists():
        continue
    reg = child.registrations.first()
    if not int(reg.course.number[:3]) >= 250:
        continue
    for absence in child.absence_set.all():
        if absence.session.date == date(2020, 1, 11):
            absence.delete()


for child in Child.objects.prefetch_related("registrations"):
    if not child.registrations.exists():
        continue
    latest_registration = child.registrations.first()
    if not latest_registration.course.number[:2] in ("27",):
        continue
    date_dict = {}
    for absence in child.absence_set.all():
        if absence.session.date in date_dict:
            date_dict[absence.session.date].append(absence)
        else:
            date_dict[absence.session.date] = [absence]
    for dates in date_dict.values():
        if len(dates) > 1:
            to_keep = []
            latest_absence = None
            for absence in dates:
                if absence.session.course == latest_registration.course:
                    to_keep.append(absence)
                    continue
                if absence.session.course.number[:2] == latest_registration.course.number[:2]:
                    to_keep.append(absence)
                    continue
            if len(to_keep) == 1:
                to_remove = Absence.objects.filter(
                    pk__in=[absence.pk for absence in dates if absence != to_keep[0]]
                )
                to_remove.delete()
                continue
            print((child.registrations.first()))
            for count, absence in enumerate(to_keep):
                print(("{} - {} - {}".format(count + 1, absence.modified, absence)))
            chosen_num = input("Choose num: ")
            if not chosen_num:
                continue
            num = int(chosen_num) - 1
            Absence.objects.filter(
                pk__in=[absence.pk for absence in dates if absence != dates[num]]
            ).delete()


for child in Child.objects.all():
    date_dict = {}
    for absence in child.absence_set.all():
        if absence.session.date in date_dict:
            date_dict[absence.session.date].append(absence)
        else:
            date_dict[absence.session.date] = [absence]
    for dates in date_dict.values():
        if len(dates) > 1:
            for absence in dates:
                if absence.status != "present":
                    print(dates)
                    break

for child in Child.objects.all():
    date_dict = {}
    for absence in child.absence_set.all():
        if absence.session.date in date_dict:
            date_dict[absence.session.date].append(absence)
        else:
            date_dict[absence.session.date] = [absence]
    for dates in date_dict.values():
        if len(dates) > 1:
            print((child.registrations.last()))
            for count, absence in enumerate(dates):
                print(("{} - {} - {}".format(count + 1, absence.modified, absence)))
            num = int(eval(input("Choose num: "))) - 1
            if not num:
                continue
            Absence.objects.filter(
                pk__in=[absence.pk for absence in dates if absence != dates[num]]
            ).delete()


for child in Child.objects.all():
    date_dict = {}
    for absence in child.absence_set.all():
        if absence.session.date in date_dict:
            date_dict[absence.session.date].append(absence)
        else:
            date_dict[absence.session.date] = [absence]
    if len(date_dict[datetime.date(2020, 1, 11)]) > 1:
        pass

for date, absences in date_dict.items():
    if len(absences) > 1:
        if date == datetime.date(2020, 1, 11):
            pass
        print(date_dict)
        for count, absence in enumerate(dates):
            print(("{} - {} - {}".format(count + 1, absence.modified, absence)))
        num = int(eval(input("Choose num: "))) - 1
        Absence.objects.filter(
            pk__in=[absence.pk for absence in dates if absence != dates[num]]
        ).delete()


missing = 0
for session in Session.objects.filter(date__gte=datetime.datetime.now()):
    for registration in session.course.participants.all():
        if not Absence.objects.filter(child=registration.child, session=session).exists():
            missing += 1
        # absence, created=Absence.objects.get_or_create(
        #    child=registration.child, session=session,
        #    defaults={'status': Absence.STATUS.present}
        # )
