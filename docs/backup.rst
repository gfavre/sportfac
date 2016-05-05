Backup whole database
=====================

mkdir ../backup
python manage.py dumpdata flatpages > ../backup/flatpages.json
python manage.py dumpdata profiles.SchoolYear profiles.Teacher > ../backup/school.json
python manage.py dumpdata auth.Group profiles.familyUser > ../backup/users.json
python manage.py dumpdata profiles.Child > ../backup/children.json
python manage.py dumpdata activities > ../backup/activities.json
python manage.py dumpdata profiles.Registration profiles.ExtraInfo > ../backup/registrations.json
python manage.py dumpdata mailer > ../backup/mail.json


Reload backup
=============

Moving from non multi db to multidb
-----------------------------------
sed 's/profiles\.teacher/schools\.teacher/g' ../backup/users.json > ../backup/users-model1.json
sed 's/profiles\.child/registrations\.child/g' ../backup/users-model1.json > ../backup/users-fixed.json
python manage.py tenant_command loaddata ../backup/users-fixed.json 


sed 's/profiles\.teacher/schools\.teacher/g' ../backup/school.json > ../backup/school-fixed.json
python manage.py tenant_command loaddata ../backup/school-fixed.json





sed 's/profiles\.registration/registrations\.registration/g' ../backup/registrations.json > ../backup/registrations-model1.json
sed 's/profiles\.extrainfo/registrations\.extrainfo/g' ../backup/registrations-model1.json > ../backup/registrations-fixed.json
rm ../backup/registrations-model1.json
python manage.py tenant_command loaddata ../backup/registrations-fixed.json



python manage.py loaddata ../backup/flatpages.json


python manage.py loaddata ../backup/activities.json
python manage.py loaddata ../backup/mail.json




Otherwise
---------
python manage.py loaddata ../backup/registrations.json

