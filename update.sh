#!/bin/sh
PROJECT=`basename "$VIRTUAL_ENV"`
echo $PROJECT
WORKER="${PROJECT}_worker"
BEAT="${PROJECT}_beat"

supervisorctl stop $PROJECT
supervisorctl stop $WORKER
supervisorctl stop $BEAT
git pull
pip install -r requirements/production.txt
python sportfac/manage.py migrate
python sportfac/manage.py collectstatic --noinput
supervisorctl start $PROJECT
supervisorctl start $WORKER
supervisorctl start $BEAT

