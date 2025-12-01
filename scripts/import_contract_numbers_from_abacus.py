"""
This script imports all contract number, associated with the functions where available
"""

import pandas as pd
from django.core.exceptions import MultipleObjectsReturned

from activities.models import CoursesInstructors
from payroll.models import Function
from profiles.models import FamilyUser


COLUMN_EXTERNAL_ID = "N° P"
COLUMN_FUNCTION_NAME = "Désignation du contrat"
COLUMN_CONTRACT_NUMBER = "N° C"
COLUMN_COURSE_ID = "course_id"  # Adapt if needed
COLUMN_FIRST_NAME = "Prénom"
COLUMN_LAST_NAME = "Nom"

FUNCTION_SYNONYMS = {
    "Moniteur·trice SSF": "Moniteur SSF",
    "Surveillant·e SSF": "Surveillant SSF",
    "Manutentionnaire (skis et équip)": "Manutentionnaire SSF",
    "Moniteur·trice SSF MEP": "Moniteur SSF MEP",
    "Organisateur·trice SSF": "Organisateur SSF",
    "Auxiliaire (jeunes)": "Auxiliaire jeune",
}


def load_dataframe(path: str) -> pd.DataFrame:
    return pd.read_excel(path)


def get_family_user(external_id: str):
    try:
        return FamilyUser.objects.get(external_identifier=external_id)
    except FamilyUser.DoesNotExist:
        return None


def get_function_by_name(name: str):
    name = FUNCTION_SYNONYMS.get(name, name)
    try:
        return Function.objects.get(name=name)
    except Function.DoesNotExist:
        return None
    except MultipleObjectsReturned:
        print(f"Multiple Function entries match the name: {name}")
        return None


def get_family_user_from_external_id_and_function(external_id: str, function: Function):
    """
    Return the FamilyUser that is linked to the given function via CoursesInstructors.
    Avoids MultipleObjectsReturned errors.
    """
    users = FamilyUser.objects.filter(external_identifier=external_id)

    if not users.exists():
        return None

    # Restrict to users that have this function via CoursesInstructors
    users_with_function = users.filter(coursesinstructors__function=function).distinct()

    if users_with_function.count() == 1:
        return users_with_function.first()

    # Ambiguous case: cannot determine reliably
    return None


def process_row(row: pd.Series):
    """
    Process a single row: validate and update CoursesInstructors.

    Args:
        row: A pandas Series representing a row of the file.
    """
    external_id = str(row[COLUMN_EXTERNAL_ID]).strip()
    function_name = str(row[COLUMN_FUNCTION_NAME]).strip()
    contract_number = str(row[COLUMN_CONTRACT_NUMBER]).strip()
    full_name = str(row[COLUMN_FIRST_NAME]).strip() + " " + str(row[COLUMN_LAST_NAME]).strip()

    # Empty strings → None (required for unique constraint logic)
    if contract_number == "":
        contract_number = None
    user = get_family_user(external_id)
    if user is None:
        # too many possible users, or none matches this function
        return
    function = get_function_by_name(function_name)
    if function is None:
        print(f"Function {function_name} not found.")
        return

    qs = CoursesInstructors.objects.filter(instructor=user, function=function)

    if not qs.exists():
        return

    # 1) Clear all numbers first (to avoid unique constraint conflicts)
    qs.update(contract_number=None)

    # 2) Assign the new contract number once all rows are clean
    if contract_number:
        qs.update(contract_number=contract_number)

    print(
        f"Updated contract_number={contract_number} for instructor {full_name} and function {function_name} "
        f"in {qs.count()} rows."
    )


# @transaction.atomic
def import_contracts(path: str):
    """
    Main import function. Loads the file, iterates rows, updates CoursesInstructors.

    Args:
        path: Path to the XLSX file.
    """
    df = load_dataframe(path)

    for _, row in df.iterrows():
        process_row(row)


import_contracts("/home/greg/temp/Contrats_passerelle_kepchup.xlsx")
