data = [
    ("138002", "Florian", "Barras"),
    ("246001", "Charlotte", "Busset"),
    ("100075", "Bernard", "Chevalley"),
    ("266002", "Thomas", "Claessens"),
    ("118003", "Cláudia António", "Dos Santos"),
    ("100734", "Lisa", "Druey"),
    ("296001", "Aurélie", "Dupraz"),
    ("100632", "Gilles", "Dupraz"),
    ("296003", "Ludovic", "Dupraz"),
    ("100358", "Carolanne", "Feissli"),
    ("373001", "Joël", "Fürst"),
    ("424003", "Sonia", "Gerard"),
    ("100893", "Gaël", "Gremaud"),
    ("100215", "Manfred", "Grübel"),
    ("498001", "Vincent", "Huther"),
    ("100082", "François", "Iff"),
    ("535001", "Maeva", "Keck"),
    ("100533", "Marco", "Moreira"),
    ("680002", "Georges", "Nicole"),
    ("696001", "Laurent", "Ortuno"),
    ("706006", "Federico", "Pellacani"),
    ("726007", "Laura", "Ramseier"),
    ("100077", "Daniel", "Renevey"),
    ("100171", "Francine", "Renevey"),
    ("100555", "Sébastien", "Renevey"),
    ("736002", "Marc", "Renkens"),
    ("100843", "Renata", "Renkens"),
    ("751001", "Ludovic", "Rochat"),
    ("262002", "Emilie", "Rondel"),
    ("756001", "Gregory", "Rondel"),
    ("772002", "Perrine", "Rusconi"),
    ("100419", "Carine", "Sandmeier"),
    ("100633", "Mario", "Sandmeier"),
    ("885004", "Tiphaine", "Sandmeier"),
    ("100933", "Céline", "Sarrasin"),
    ("789004", "Sandrine", "Siu"),
    ("100079", "Stéphane", "Thélin"),
    ("100093", "Nicola", "Vacchini"),
]

from profiles.models import FamilyUser
from django.core.exceptions import MultipleObjectsReturned
for external_identifier, first_name, last_name in data:
    try:
        user = FamilyUser.objects.get(first_name=first_name, last_name=last_name)
    except FamilyUser.DoesNotExist:
        print("Could not find user {} {}".format(first_name, last_name))
        continue
    except MultipleObjectsReturned:
        print("Multiple users found for {} {}".format(first_name, last_name))
        continue
    user.external_identifier = external_identifier
    user.save()
