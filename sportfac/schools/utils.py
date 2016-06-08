#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
from datetime import datetime

from django.utils.translation import ugettext as _
from django.utils.six import moves

import xlrd


from .models import Teacher
from registrations.models import Child
from profiles.models import SchoolYear


TEACHER_MANDATORY_FIELDS = (u'ID LAGAPEO', u'Nom', u'Prénom', u'Maîtrises')
TEACHER_IMPORT_TO_FIELD = {u'ID LAGAPEO': 'number', 
                   u'Nom': 'last_name', 
                   u'Prénom': 'first_name', 
                   u'Courriel 1': 'email',}
def load_teachers(filelike):            
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


CHILD_MANDATORY_FIELDS = (u'ID LAGAPEO', u'Nom', u'Prénom', u'Genre', u'Date de naissance', u'Nationalité', u'Langue maternelle')
CHILD_IMPORT_TO_FIELD = {
    u'ID LAGAPEO': 'id_lagapeo', 
    u'Nom': 'last_name', 
    u'Prénom': 'first_name', 
    u'Courriel 1': 'email',}

class ChildParser:

    def __init__(self):
        self.fields_dict = {
            u'ID LAGAPEO': ('id_lagapeo', lambda x: int(x)), 
            u'Nom': ('last_name', lambda x: x), 
            u'Prénom': ('first_name', lambda x: x),
            u'Genre': ('sex', self.parse_sex),
            u'Date de naissance': ('birth_date', self.parse_birth_date),
            u'Nationalité': ('nationality', self.parse_nationality),
            u'Langue maternelle': ('language', self.parse_language)
        }

    def parse_sex(self, value):
        if value == 'G':
            return Child.SEX.M
        return Child.SEX.F

    def parse_birth_date(self, value):
        try:
            return datetime.strptime(value, '%d.%m.%Y').date()
        except ValueError:
            return None
    
    def parse_nationality(self, value):
        if value == 'Suisse':
            return Child.NATIONALITY.CH
        elif value == 'Liechtenstein':
            return Child.NATIONALITY.FL
        else:
            return Child.NATIONALITY.DIV 
    
    def parse_language(self, value):
        if value == u'Français':
            return Child.LANGUAGE.F
        elif value == u'Italien':
            return Child.LANGUAGE.I
        elif value == u'Allemand':
            return Child.LANGUAGE.D
        elif value == u'Anglais':
            return Child.LANGUAGE.E
        else:
            return None
    
    def parse(self, row):
        out = {}
        for key, val in row.items():
            translated, fct = self.fields_dict.get(key, (None, None))
            if translated:
                out[translated] = fct(val)
        return out

            
    


def load_children(filelike):
    try:
        xls_book = xlrd.open_workbook(file_contents=filelike.read())
        sheet = xls_book.sheets()[0]
        header_row = sheet.row_values(0)
                
        if not all(key in header_row for key in CHILD_MANDATORY_FIELDS):
            raise ValueError(_("All these fields are mandatory: %s") % unicode(CHILD_MANDATORY_FIELDS))
    except xlrd.XLRDError:
        raise ValueError(_("File format is unreadable"))
    nb_created = 0
    nb_updated = 0
    nb_skipped = 0
    
    parser = ChildParser()
    for i in moves.range(1, sheet.nrows):
        values = dict(zip(header_row, sheet.row_values(i)))

        translated = {}
        print parser.parse(values)


"""
import re
from datetime import datetime

from django.utils.translation import ugettext as _
from django.utils.six import moves

import xlrd
from registrations.models import Child
from profiles.models import SchoolYear

from schools.utils import ChildParser

f = open('/Users/grfavre/Desktop/exportExcel_ssf.xlsx')
xls_book = xlrd.open_workbook(file_contents=f.read())
sheet = xls_book.sheets()[0]
header_row = sheet.row_values(0)
parser = ChildParser()
for i in moves.range(1, sheet.nrows):
    values = dict(zip(header_row, sheet.row_values(i)))
    print parser.parse(values)

"""