from activities.models import Course

from absences.models import Session, Absence
from registrations.models import Registration

for course in Course.objects.all():
    children = [r.child for r in course.participants.all()]
    for session in course.sessions.all():
        for absence in list(session.absences.all()):
            if absence.child not in children:
                print(u'c:{} - delete absence'.format(course))
                absence.delete()


for registration in Registration.objects.all():
    Absence.objects.filter(child=registration.child, session__date__gt=registration.modified)\
                   .exclude(session__course=registration.course)\
                   .delete()

from registrations.models import Child

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


for child in Child.objects.all():
    date_dict = {}
    for absence in child.absence_set.all():
        if absence.session.date in date_dict:
            date_dict[absence.session.date].append(absence)
        else:
            date_dict[absence.session.date] = [absence]
    for dates in date_dict.values():
        if len(dates) > 1:
            for count, absence in enumerate(dates):
                print('{} - {} - {}'.format(count + 1, absence.modified, absence))
            num = int(raw_input('Choose num: ')) - 1
            Absence.objects.filter(pk__in=[absence.pk for absence in dates if absence!=dates[num]]).delete()


