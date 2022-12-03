from __future__ import absolute_import, print_function

from activities.models import Course
from six.moves import input


for c in Course.objects.all():
    sessions = c.sessions.filter(instructor=None)
    if sessions.exists():
        if c.instructors.count() == 1:
            i = c.instructors.first()
        else:
            print(("\n".join(["{} - {}".format(m.pk, m.full_name) for m in c.instructors.all()])))
            try:
                pk = int(input("Default Instructor? "))
                i = c.intructors.get(pk=pk)
            except:
                continue
    for s in sessions:
        s.instructor = i
        s.save()
