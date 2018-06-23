Server configuration
====================

Choose project_name, something like sportfac_city

1. Create domain: https://my.webfaction.com/new-domain
2. Create email: https://my.webfaction.com/new-email
3. Create database: https://my.webfaction.com/new-database:
    Type: PostgreSQL
    database owner: create new, note password


Code
====

Duplicate existing fabfile in /deploy

fabsettings.py
--------------
[] project_name
[] database
[] email address
[] redis db, using number of deploy directories + 1, e.g 'redis://localhost:14387/8'

fabfile.py
----------
[] change `env.settings`
[] change `env.subdomains`


Django
======

[] Duplicate existing account in `sportfac/sportfac/settings/` with name matching `env.settings`
[] Duplicate `sportfac/templates/themes/...` set name matching with `TEMPLATES` setting in settings file

Templates
---------
[] Setup address.html. This will fill footer.
[] modify default title in base.html
[] modify main-title.html (top left brand...)
[] modify contact/contact.html


Deploy
======

[] Git add...
[] cd deploy/city
[] ssh-add ~/.ssh/id_rsa
[] fab install_app
if it fails when generating virtualenv, copy another one from server: cpvirtualenv sportfac_montreux <destination>,
clean bin/postactivate, modify .project.
[] python sportfac/manage.py migrate_schemas --shared
[] python sportfac/manage.py createsuperuser
[] python sportfac/manage.py create_tenant
    schema_name: period_20180827_20190105
    status: creating
    start date: 2018-08-27
    end date: 2019-01-05
    domain: 2018-08-27-2019-01-05
    is primary (leave blank to use 'True'): True
    is current: True
[] python sportfac/manage.py shell
    from backend.models import Domain, YearTenant
    YearTenant.objects.first().create_schema(check_if_exists=True, verbosity=3)

Postdeploy - webfaction
=======================
[] Rename website to <project>_no_ssl.
[] create website <project> that will use ssl for the domains.


Postdeploy - Django admin
=========================

Sites
-----
[] Modify default site: /admin/sites/site/1/change/, use domain name without protocol for both fields

Dynamic preferences
-------------------
[] change every field. From_email: mail as created in webfaction.

Users
-----
[] Create Remo
[] Create local admins

Flatpages / pages statiques
---------------------------
[] create homepage, url: /
[] create /protection-des-donnees/ title: Protection des données, text: copy from another instance
[] create /reglement/ title: Règlement de participation


Backend
=======
Setup first opening period as mentioned by user.
