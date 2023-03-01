# -*- coding: utf-8 -*-
import os
from tempfile import NamedTemporaryFile

from django.core.management import call_command
from django.db import connection

from activities.models import Course
from backend.models import Domain


source_domain = Domain.objects.get(domain="periode_initiale")
destination_domain = Domain.objects.get(domain="2021-07-01")


connection.set_tenant(source_domain.tenant)
f = NamedTemporaryFile(suffix=".json", delete=False)
call_command("dumpdata", "activities", output=f.name)
f.close()


connection.set_tenant(destination_domain.tenant)
call_command("loaddata", f.name)
os.remove(f.name)
Course.objects.all().update(uptodate=False)
