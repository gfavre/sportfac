import csv

from django.core.management.base import BaseCommand
from django.db import transaction

from ...models import City


def unicode_csv_reader(utf8_data, **kwargs):
    csv_reader = csv.reader(utf8_data, **kwargs)
    for row in csv_reader:
        yield list(row)


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
                (created, updated) = self.load_db(database_file)
                print(f"Created {created} cities, updated {updated} cities from {database_file}")

    @staticmethod
    def load_db(filename):
        nb_created = 0
        nb_updated = 0
        with open(filename, encoding="utf-8") as csv_file:
            for line in unicode_csv_reader(csv_file, delimiter="\t"):
                country = line[0]
                zipcode = line[1]
                city = line[2]
                _, created = City.objects.get_or_create(zipcode=zipcode, country=country, defaults={"name": city})
                if created:
                    nb_created += 1
                else:
                    nb_updated += 1
        return (nb_created, nb_updated)
