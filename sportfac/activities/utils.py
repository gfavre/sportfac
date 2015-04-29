from sportfac.utils import ExcelWriter


JS_CSV_COLUMNS = ('NO_PERS_BDNJS','SEXE','NOM','PRENOM',
                  'DAT_NAISSANCE','RUE','NPA','LOCALITE',
                  'PAYS','NATIONALITE','1ERE_LANGUE','CLASSE/GROUPE')

def course_to_js_csv(course, filelike):
    writer = ExcelWriter(filelike, )
    writer.writerow(JS_CSV_COLUMNS)
    rows = []
    for registration in course.participants.all():
        child = registration.child
        family = registration.child.family
        rows.append(('', child.js_sex, child.last_name, child.first_name.title(),
                     child.js_birth_date, 
                     family.address, family.zipcode, family.city, family.country, 
                     child.nationality, child.language, course.get_js_name
        ))
    writer.writerows(rows)
    