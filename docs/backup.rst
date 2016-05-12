Backup whole database
=====================

mkdir ../backup
python manage.py dumpdata flatpages > ../backup/flatpages.json
python manage.py dumpdata profiles.SchoolYear > ../backup/school-years.json
python manage.py dumpdata profiles.Teacher > ../backup/teachers.json
python manage.py dumpdata auth.Group profiles.familyUser > ../backup/users.json
python manage.py dumpdata profiles.Child > ../backup/children.json
python manage.py dumpdata activities > ../backup/activities.json
python manage.py dumpdata profiles.Registration  > ../backup/registrations.json
python manage.py dumpdata profiles.ExtraInfo  > ../backup/extra.json

python manage.py dumpdata mailer > ../backup/mail.json
python manage.py dumpdata database > ../backup/constance.json


Reload backup
=============

Migrate
-------
python manage.py migrate_schemas --shared
python manage.py shell:

from datetime import datetime, timedelta

from django.conf import settings
from constance.admin import config

from backend.models import YearTenant, Domain

tenant = YearTenant(
    schema_name='period_20150801_20160731',
    start_date=datetime(2015, 8, 1),
    end_date=datetime(2016, 7, 31),
    status='ready'
)
tenant.save()
tenant.create_schema(check_if_exists=True)

domain = Domain()
domain.domain = '2015-2016'
domain.tenant = tenant
domain.is_current = True
domain.is_primary = True
domain.save()


Moving from non multi db to multidb
-----------------------------------
python manage.py loaddata ../backup/school-years.json

sed 's/profiles\.teacher/schools\.teacher/g' ../backup/teachers.json > ../backup/teachers-fixed.json
python manage.py tenant_command loaddata ../backup/teachers-fixed.json


sed 's/profiles\.teacher/schools\.teacher/g' ../backup/users.json > ../backup/users-fixed.json
python manage.py loaddata ../backup/users-fixed.json 

sed 's/profiles\.teacher/schools\.teacher/g' ../backup/children.json > ../backup/children-model1.json
sed 's/profiles\.child/registrations\.child/g' ../backup/children-model1.json > ../backup/children-fixed.json
rm ../backup/children-model1.json
python manage.py tenant_command loaddata ../backup/children-fixed.json 

python manage.py loaddata ../backup/flatpages.json

python manage.py tenant_command loaddata ../backup/activities.json

sed 's/profiles\.registration/registrations\.registration/g' ../backup/registrations.json > ../backup/registrations-model1.json
sed 's/profiles\.child/registrations\.child/g' ../backup/registrations-model1.json > ../backup/registrations-fixed.json
rm ../backup/registrations-model1.json
python manage.py tenant_command loaddata ../backup/registrations-fixed.json

sed 's/profiles\.extrainfo/registrations\.extrainfo/g' ../backup/extra.json > ../backup/extra-fixed.json
python manage.py tenant_command loaddata ../backup/extra-fixed.json

python manage.py loaddata ../backup/mail.json
python manage.py tenant_command loaddata ../backup/constance.json
