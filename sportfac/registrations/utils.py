# -*- coding: utf-8 -*-
from datetime import datetime

from django.utils.six import moves
from django.utils.translation import ugettext as _

import xlrd

from registrations.models import Child


CHILD_MANDATORY_FIELDS = (u'ID LAGAPEO', u'Nom', u'Prénom', u'Genre', u'Date de naissance', u'Nationalité', u'Langue maternelle')
CHILD_IMPORT_TO_FIELD = {
    u'ID LAGAPEO': 'id_lagapeo',
    u'Nom': 'last_name',
    u'Prénom': 'first_name',
    u'Courriel 1': 'email',}


class ChildParser:

    def __init__(self, book=None):
        if book:
            self.datemode = book.datemode
        else:
            self.datemode = 0
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
            if isinstance(value, basestring):
                return datetime.strptime(value, '%d.%m.%Y').date()
            else:
                return xlrd.xldate_as_datetime(value, self.datemode)
        except ValueError:
            return None
        except TypeError:
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

        return Child.LANGUAGE.F

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

    parser = ChildParser(xls_book)
    for i in moves.range(1, sheet.nrows):
        values = dict(zip(header_row, sheet.row_values(i)))
        try:
            parsed = parser.parse(values)
        except:
            continue
        id_lagapeo = parsed.pop('id_lagapeo')
        child, created = Child.objects.update_or_create(id_lagapeo=id_lagapeo, defaults=parsed)
        if created:
            nb_created += 1
        else:
            nb_updated += 1
    return (nb_created, nb_updated)

"""
import re

from django.utils.translation import ugettext as _
from django.utils.six import moves

import xlrd

from registrations.utils import ChildParser

f = open('/Users/grfavre/Desktop/exportExcel_ssf.xlsx')
xls_book = xlrd.open_workbook(file_contents=f.read())
sheet = xls_book.sheets()[0]
header_row = sheet.row_values(0)
parser = ChildParser()
for i in moves.range(1, sheet.nrows):
    values = dict(zip(header_row, sheet.row_values(i)))
    print parser.parse(values)

"""
