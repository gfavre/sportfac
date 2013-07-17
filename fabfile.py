# -*- coding: utf-8 -*-
"""
This fabfile deploys django apps on webfaction using gunicorn,
and supervisor.
"""
import os, re, xmlrpclib, sys, xmlrpclib, os.path, httplib, random

from fabric.api import *
from fabric.contrib.console import confirm
from fabric.contrib.files import sed, exists, upload_template, append
from fabric.utils import abort
from fabric.context_managers import prefix, path
from fabric.operations import put

try:
    from fabsettings import WF_HOST, PROJECT_NAME, REPOSITORY, USER, PASSWORD, \
                            VIRTUALENVS, SETTINGS_SUBDIR, \
                            DBNAME, DBUSER, DBPASSWORD, \
                            MAILHOST, MAILUSER, MAILPASSWORD, MAILADDRESS
except ImportError:
    print("""
ImportError: Couldn't find fabsettings.py, it either does not exist or is
missing specific settings.
It should be of this form:

WF_HOST         = "web392.webfaction.com"
PROJECT_NAME    = "sportfac"
REPOSITORY      = "https://grfavre@kis-git.epfl.ch/repo/sportfac.git"
USER            = "grfavre"
PASSWORD        = "************"
DBNAME          = "sportfac"
DBUSER          = "sportfac"
DBPASSWORD      = "************"
SETTINGS_SUBDIR = "sportfac"
VIRTUALENVS     = "/home/grfavre/.virtualenvs"
MAILHOST        = "smtp.webfaction.com"
MAILUSER        = "grfavre"
MAILPASSWORD    = PASSWORD
MAILADDRESS     = "gregory@dealguru.ch"

""")
    sys.exit(1)

class _WebFactionXmlRPC():
    def __init__(self, user, password):
        API_URL = 'https://api.webfaction.com/'
        try:
            http_proxy = os.environ['http_proxy']
        except KeyError:
            http_proxy = None
        self.server = xmlrpclib.Server(API_URL, transport=http_proxy)
        self.session_id, self.account = self.login(user, password)
    
    def login(self, user, password):
        return self.server.login(user, password)
    
    def __getattr__(self, name):
        def _missing(*args, **kwargs):
            return getattr(self.server, name)(self.session_id, *args, **kwargs)
        return _missing

env.local_config_dir  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
env.hosts             = [WF_HOST]
env.user              = USER
env.password          = PASSWORD
env.project           = PROJECT_NAME
env.settings          = 'production'
env.dbname            = DBNAME
env.dbuser            = DBUSER
env.dbpassword        = DBPASSWORD
env.dbtype            = 'postgresql'
env.home              = os.path.join("/home/", USER)
env.repo              = REPOSITORY
env.project_dir       = os.path.join(env.home, 'webapps', PROJECT_NAME)
env.settings_dir      = os.path.join(env.project_dir, SETTINGS_SUBDIR)
env.supervisor_dir    = os.path.join(env.home, 'webapps', 'supervisor')
env.virtualenv_dir    = VIRTUALENVS
env.virtualenv        = VIRTUALENVS + '/' + env.project
env.supervisor_ve_dir = os.path.join(env.virtualenv_dir, '/supervisor')
env.webfaction        = _WebFactionXmlRPC(USER, PASSWORD)
env.supervisor_cfg    = '%s/conf.d/%s.conf' % (env.supervisor_dir, env.project)
env.mailhost          = MAILHOST
env.mailuser          = MAILUSER
env.mailpassword      = MAILPASSWORD
env.mailaddress       = MAILADDRESS


def bootstrap():
    "Initializes python libraries"
    run('mkdir -p %s/lib/python2.7' % env.home)
    run('easy_install-2.7 pip')
    run('pip-2.7 install virtualenv virtualenvwrapper')



def _create_db():
    print("Creating db %s..." % env.dbname)
    for db_info in env.webfaction.list_dbs():
        if db_info['name'] == env.dbname:
            print("Database already exists")
            return
    
    env.webfaction.create_db(env.dbname, env.dbtype, env.dbpassword)
    print("... done.")


def _create_static_app():
    print("Creating static app...")
    app_name = env.project + '_static'
    for app_info in env.webfaction.list_apps():
        if app_info['name'] == app_name:
            return
    
    env.webfaction.create_app(env.project + '_static', 'static_only', False, '')    


def _create_main_app():
    print("Creating main app...")
    app_name = env.project
    for app_info in env.webfaction.list_apps():
        if app_info['name'] == app_name:
            env.app_port = app_info['port']
            return
        
    port = env.webfaction.create_app(env.project, 'custom_app_with_port', False, '')
    
def configure_supervisor():
    print("Configuring supervisor...")
    if not 'app_port' in env:
    	for app_config in env.webfaction.list_apps():
    		if app_config.get('name') == env.project:
    			env.app_port = app_config.get('port')
    			break
    require('app_port')
    upload_template(os.path.join(env.local_config_dir, 'gunicorn.conf'),
                    env.supervisor_cfg, env)

    reload_supervisor()
 
def configure_webfaction():
    _create_db()
    _create_static_app()
    _create_main_app()

def install_app():
    "Installs the django project in its own wf app and virtualenv"
    configure_webfaction()
    print("Grabbing sources...")
    with cd(env.home + '/webapps'):
        if not exists(env.project_dir + '/setup.py'):
            run('git clone %s %s' % (env.repo, env.project_dir))
    
    print("Creating virtualenv...")
    _create_ve(env.project)
    configure_supervisor()
            
    reload_app()
    restart_app()



def reload_app(arg=None):
    "Pulls app and refreshes requirements"
    with cd(env.project_dir):
        run('git pull origin master')
    
    if arg <> "quick":
        with cd(env.project_dir):
            _ve_run(env.project, "pip install -r requirements.txt")
            djangoadmin('syncdb')
            djangoadmin('migrate')
            djangoadmin('collectstatic --noinput')
    
    restart_app()


def reload_supervisor():
    "Reload supervisor config"
    with cd(env.supervisor_dir):
        _ve_run('supervisor','supervisorctl reread && supervisorctl reload')

def restart_app():
    "Restarts the app using supervisorctl"
    with cd(env.supervisor_dir):            
        _ve_run('supervisor','supervisorctl restart %s' % env.project)




### Helper functions

def _create_ve(name):
    """creates virtualenv using virtualenvwrapper
    """
    env.secretkey = ''.join([random.SystemRandom().choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(50)])
    
    if not exists(env.virtualenv_dir + '/name'):
        with cd(env.virtualenv_dir):
            run('mkvirtualenv -p /usr/local/bin/python2.7 --no-site-packages %s' % name)
    else:
        print("Virtualenv with name %s already exists. Skipping.") % name
    upload_template(os.path.join(env.local_config_dir, 'postactivate.tpl'),
                    os.path.join(env.virtualenv, 'bin', 'postactivate'), 
                    env)
    append(os.path.join(env.virtualenv, '.project'), env.project_dir)

    
    

def _ve_run(ve, cmd):
    """virtualenv wrapper for fabric commands"""
    run("""/bin/bash -l -c 'source %s/bin/virtualenvwrapper.sh && workon %s && %s'""" % (env.home, ve, cmd))

def djangoadmin(cmd):
    _ve_run(env.project, "django-admin.py %s" % cmd)


def nero():
    _ve_run('supervisor', 'supervisorctl stop %s' % env.project)
    run('rm -rf %s' % env.supervisor_cfg)
    
    try:
        env.webfaction.delete_app(env.project + '_static')
    except xmlrpclib.Fault, msg:
        print("Unable to delete static app (%s)") % msg
    try:
        env.webfaction.delete_app(env.project)
    except xmlrpclib.Fault, msg:
        print("Unable to delete main app (%s)") % msg
    
    
    try:
        env.webfaction.delete_db(env.dbname, env.dbtype)
    except xmlrpclib.Fault, msg:
        print("Unable to delete db (%s)") % msg
    
    try:
        env.webfaction.delete_db_user(env.dbuser,  env.dbtype)
    except xmlrpclib.Fault, msg:
        print("Unable to delete db user %s:\n%s") % (env.dbuser, msg)
    

def test():
    run("hostname")
    with cd(env.home + '/webapps'):
        if not exists(env.project_dir + '/setup.py'):
            run('git clone %s %s' % (env.repo, env.project_dir))
    
    put('config/gunicorn.conf', '%s/conf.d/%s.conf' % (env.supervisor_dir, env.project))