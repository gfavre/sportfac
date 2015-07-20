Install
=========

This is where you write how to get a new laptop to run this project.

.. code-block:: shell
  
   export PROJECT=nyon
   
   export BASE_DIR=~/Documents/Projets
   export PROJECT_NAME=sportfac_$PROJECT
   export PROJECT_DIR=$BASE_DIR/$PROJECT_NAME
   export DB_NAME=$PROJECT_NAME
   export DB_USER=$PROJECT_NAME
   export DB_PASSWORD=$PROJECT_NAME
   export VENVDIR=~/.virtualenvs/$PROJECT_NAME
   
   git clone http://git.pygreg.ch/sportfac.git $PROJECT_DIR
   cd $PROJECT_DIR
   git checkout -b $PROJECT
   git push --set-upstream origin $PROJECT
   mkvirtualenv $PROJECT_NAME
   echo `pwd` > $VENVDIR/.project
   
   # Database
   echo "CREATE ROLE $DB_USER WITH LOGIN UNENCRYPTED PASSWORD '$DB_PASSWORD'" | psql --user postgres
   echo "CREATE DATABASE $DB_NAME WITH OWNER=$DB_USER" | psql --user postgres
   
   # Env vars
   echo "export PYTHONPATH=$PROJECT_DIR/sportfac" >> $VENVDIR/bin/postactivate
   echo 'export DJANGO_SETTINGS_MODULE="sportfac.settings.local"' >> $VENVDIR/bin/postactivate
   echo "export DB_USER=$DB_USER" >> $VENVDIR/bin/postactivate
   echo "export DB_PASSWORD=$DB_PASSWORD" >> $VENVDIR/bin/postactivate
   echo "export DB_NAME=$DB_NAME" >> $VENVDIR/bin/postactivate
   echo "export SECRET_KEY=gdhsagkdahjsg" >> $VENVDIR/bin/postactivate
   echo "export PHANTOMJS=/usr/local/bin/phantomjs" >> $VENVDIR/bin/postactivate
   
   
   # soft
   pip install -r requirements/local.txt
   django-admin syncdb
   django-admin migrate
   django-admin loaddata sportfac/sportfac/fixtures/flatpages.json