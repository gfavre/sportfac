from activities.models import Course



for course in Course.objects.all():
    children = [r.child for r in course.participants.all()]
    for session in course.sessions.all():
        for absence in list(session.absences.all()):
            if absence.child not in children:
                print(u'c:{} - delete absence'.format(course))
                absence.delete()
