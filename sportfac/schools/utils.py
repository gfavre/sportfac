# -*- coding: utf-8 -*-
import re

from django.db.models import Min, Max
from django.utils.translation import ugettext as _
from django.utils.six import moves

import xlrd


from .models import Teacher
from profiles.models import SchoolYear


TEACHER_MANDATORY_FIELDS = (u'ID LAGAPEO', u'Nom', u'Prénom', u'Maîtrises')
TEACHER_IMPORT_TO_FIELD = {
    u'ID LAGAPEO': 'number',
    u'Nom': 'last_name',
    u'Prénom': 'first_name',
    u'Courriel 1': 'email',
}
YEARS_MINMAX = SchoolYear.objects.all().aggregate(Min('year'), Max('year'))
ALL_YEARS = range(YEARS_MINMAX['year__min'], YEARS_MINMAX['year__max'] + 1)


def load_teachers(filelike, building=None):
    try:
        xls_book = xlrd.open_workbook(file_contents=filelike.read())
        sheet = xls_book.sheets()[0]
        header_row = sheet.row_values(0)

        if not all(key in header_row for key in TEACHER_MANDATORY_FIELDS):
            raise ValueError(_("All these fields are mandatory: %s") % unicode(TEACHER_MANDATORY_FIELDS))
    except xlrd.XLRDError:
        raise ValueError(_("File format is unreadable"))

    nb_created = 0
    nb_updated = 0
    nb_skipped = 0
    for i in moves.range(1, sheet.nrows):
        values = dict(zip(header_row, sheet.row_values(i)))
        translated = {}
        for key, val in values.items():
            if key in TEACHER_IMPORT_TO_FIELD:
                translated[TEACHER_IMPORT_TO_FIELD[key]] = val

        number = translated.pop('number')

        classes = values.get(u'Maîtrises', '')
        if not classes:
            nb_skipped += 1
            continue

        teacher, created = Teacher.objects.update_or_create(number=number, defaults=translated)
        if building:
            teacher.buildings.add(building)
        teacher.years.clear()
        if created:
            nb_created += 1
        else:
            nb_updated += 1

        years = set()
        for classes_part in classes.split(','):
            match = re.match('(\d+)(?:\-(\d+))?[a-zA-Z]+[\d]?/\w+', classes_part.strip())
            if not match:
                # ACC or DES
                years = years.union(ALL_YEARS)
            else:
                years = years.union(match.groups())

        for year in years:
            if year is None:
                continue
            try:
                school_year = SchoolYear.objects.get(year=year)
                teacher.years.add(school_year)
            except SchoolYear.DoesNotExist:
                continue

    return nb_created, nb_updated, nb_skipped


