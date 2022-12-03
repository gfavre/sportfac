# -*- coding: utf-8 -*-
from __future__ import absolute_import

from datetime import timedelta

from activities.models import Course
from six.moves import range


for course in Course.objects.all():
    if course.sessions.exists():
        continue

    dates = [course.start_date]
    for i in range(1, course.number_of_sessions):
        dates.append(course.start_date + timedelta(days=7 * i))

    for date in dates:
        course.add_session(date)
