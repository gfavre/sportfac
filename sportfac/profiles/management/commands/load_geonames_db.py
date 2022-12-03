# -*- coding: utf-8 -*-
from __future__ import absolute_import

import csv

from django.core.management.base import BaseCommand
from django.db import transaction

import six

from ...models import City


def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
    csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
    for row in csv_reader:
        yield [six.text_type(cell, "utf-8") for cell in row]


class Command(BaseCommand):
    help = "Load Geonames cities db in local db"
    missing_args_message = (
        "No Geonames database file specified. Please provide the path of at least "
        "one file in the command line."
        ""
        "To download databases: https://www.geonames.org/export/"
    )

    def add_arguments(self, parser):
        parser.add_argument("args", metavar="database", nargs="+", help="database file")

    def handle(self, *database_files, **options):
        with transaction.atomic():
            for database_file in database_files:
                self.load_db(database_file)

    @staticmethod
    def load_db(filename):
        for line in unicode_csv_reader(open(filename), dialect="excel-tab"):
            country = line[0]
            zipcode = line[1]
            city = line[2]
            City.objects.get_or_create(zipcode=zipcode, country=country, defaults={"name": city})
