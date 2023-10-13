from sportfac.utils import ExcelWriter


JS_CSV_COLUMNS = (
    "N° PERSONNEL",
    "NOM",
    "PRENOM",
    "DATE DE NAISSANCE",
    "SEXE",
    "N_AVS",
    "PEID",
    "NATIONALITE",
    "LANGUE MATERNELLE",
    "RUE",
    "NUMERO",
    "NPA",
    "LOCALITE",
    "PAYS",
)


def course_to_js_csv(course, filelike):
    writer = ExcelWriter(
        filelike,
    )
    writer.writerow(JS_CSV_COLUMNS)
    rows = []
    for registration in course.participants.all():
        child = registration.child
        rows.append(
            (
                "",
                child.last_name,
                child.first_name.title(),
                child.js_birth_date,
                child.js_sex,
                child.js_avs or "",
                "",
                child.js_nationality,
                child.js_language,
                child.js_street,
                child.js_street_number,
                child.js_zipcode,
                child.js_city,
                child.js_country,
            )
        )
    for row in rows:
        writer.writerow(row)
