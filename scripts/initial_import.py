from __future__ import absolute_import

import csv
import datetime

from django.template.defaultfilters import slugify

from activities.models import Activity, Course, Responsible


activities = {}
responsibles = {}
days = {"lundi": 1, "mardi": 2, "mercredi": 3, "jeudi": 4, "vendredi": 5}


with open("/Users/grfavre/Desktop/cours.csv") as csvfile:
    dialect = csv.excel
    reader = csv.reader(csvfile, dialect=dialect, delimiter=";")
    next(reader)
    for (
        a_name,
        junk,
        junk,
        price,
        resp,
        nb,
        day,
        junk,
        start_date,
        end_date,
        start_time,
        end_time,
        place,
        nbmin,
        nbmax,
        year,
        trim,
    ) in reader:
        if a_name and a_name not in activities:
            activity, created = Activity.objects.get_or_create(
                name=a_name.decode("latin-1"), slug=slugify(a_name.decode("latin-1"))
            )
            activity.save()
            activities[a_name] = activity
        if resp and resp not in responsibles:
            names = resp.decode("latin-1").split(" ")
            resp_obj, created = Responsible.objects.get_or_create(
                last=len(names) > 1 and names[1] or names[0],
                first=len(names) > 1 and names[0] or "",
            )
            resp_obj.save()
            responsibles[resp] = resp_obj
        years = year.split("-")
        ymin = int(years[0])
        ymax = len(years) > 1 and int(years[1]) or ymin
        course = Course(
            activity=activities[a_name],
            responsible=responsibles[resp],
            price=int(price),
            number_of_sessions=int(nb),
            day=days[day],
            start_date=datetime.datetime.strptime(start_date, "%d.%m.%y"),
            end_date=datetime.datetime.strptime(end_date, "%d.%m.%y"),
            start_time=datetime.datetime.strptime(start_time, "%Hh%M"),
            end_time=datetime.datetime.strptime(end_time, "%Hh%M"),
            place=place.decode("latin-1"),
            min_participants=int(nbmin),
            max_participants=int(nbmax),
            schoolyear_min=ymin,
            schoolyear_max=ymax,
        )
        course.save()
