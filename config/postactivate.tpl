export PYTHONPATH=%(project_dir)s/%(project)s
export DJANGO_SETTINGS_MODULE="%(project)s.settings.%(settings)s"
export DB_USER="%(dbuser)s"
export DB_PASSWORD="%(dbpassword)s"
export DB_NAME="%(dbname)s"
export SECRET_KEY="%(secretkey)s"

