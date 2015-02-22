#!/usr/bin/python
# -*- coding: utf-8 -*-
import re

from django.utils.translation import ugettext as _
from django.utils.six import moves

from .models import Teacher, SchoolYear

import xlrd

MANDATORY_FIELDS = (u'ID LAGAPEO', u'Nom', u'Prénom', u'Maîtrises')
IMPORT_TO_FIELD = {u'ID LAGAPEO': 'number', 
                   u'Nom': 'last_name', 
                   u'Prénom': 'first_name', 
                   u'Courriel 1': 'email',}
def load_teachers(filelike):            
    try:
        xls_book = xlrd.open_workbook(file_contents=filelike.read())
        sheet = xls_book.sheets()[0]
        header_row = sheet.row_values(0)
                
        if not all(key in header_row for key in MANDATORY_FIELDS):
            raise ValueError(_("All these fields are mandatory: %s") % MANDATORY_FIELDS)
    except xlrd.XLRDError:
        raise ValueError(_("File format is unreadable"))
    
    nb_created = 0
    nb_updated = 0
    nb_skipped = 0
    for i in moves.range(1, sheet.nrows):
        values = dict(zip(header_row, sheet.row_values(i)))
        translated = {}
        for key, val in values.items():
            if key in IMPORT_TO_FIELD:
                translated[IMPORT_TO_FIELD[key]] = val
        classes = values.get(u'Maîtrises', '')
        match = re.match('(\d+)(?:\-(\d+))?[a-zA-Z]+/\w+', classes)
        if not classes or not match:
            nb_skipped += 1
            continue
        number = translated.pop('number')
        teacher, created = Teacher.objects.get_or_create(number=number, defaults=translated)
        teacher.years.clear()
        if created: 
            nb_created += 1
        else:
            nb_updated += 1
        for year in match.groups():
            try:
                school_year = SchoolYear.objects.get(year=year)
                teacher.years.add(school_year)
            except SchoolYear.DoesNotExist:
                continue
    
    return (nb_created, nb_updated, nb_skipped)

