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
    from fabsettings import (WF_HOST, APP_NAME, PROJECT_NAME, REPOSITORY, BRANCH,
                             USER, PASSWORD,
                             VIRTUALENVS, SETTINGS_SUBDIR,
                             DBNAME, DBUSER, DBPASSWORD,
                             MAILGUN_API_KEY, MAILGUN_SENDER_DOMAIN, MAILADDRESS,
                             BROKER_URL, PHANTOMJS, MEMCACHED_SOCKET)
except ImportError:
    print("""
ImportError: Couldn't find fabsettings.py, it either does not exist or is
missing specific settings.
It should be of this form:

WF_HOST          = "web392"
APP_NAME         = 'sportfac'
PROJECT_NAME     = "sportfac"
REPOSITORY       = "https://grfavre@kis-git.epfl.ch/repo/sportfac.git"
BRANCH           = 'master'
USER             = "grfavre"
PASSWORD         = "************"
DBNAME           = "sportfac"
DBUSER           = "sportfac"
DBPASSWORD       = "************"
SETTINGS_SUBDIR  = "sportfac"
VIRTUALENVS      = "/home/grfavre/.virtualenvs"
MAILGUN_API_KEY  = "key-1234567890abcdef"
MAILGUN_SENDER_DOMAIN = "mg.kepchup.ch"
MAILADDRESS      = "gregory@dealguru.ch"
BROKER_URL       = "redis://localhost:14387/0"
PHANTOMJS        = '/home/grfavre/bin/phantomjs'
MEMCACHED_SOCKET = 'memcached.sock'
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

def __concat_domain(subdomain, domain):
    if subdomain:
        if subdomain != '.':
            return subdomain + '.' + domain
        else:
            return '.' + domain
    return domain


env.local_config_dir  = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config')
env.machine           = WF_HOST
env.hosts             = [WF_HOST.lower() + '.webfaction.com']
env.user              = USER
env.password          = PASSWORD
env.project           = PROJECT_NAME
env.app_name          = APP_NAME
env.settings          = 'montreux'
env.dbname            = DBNAME
env.dbuser            = DBUSER
env.dbpassword        = DBPASSWORD
env.dbtype            = 'postgresql'
env.home              = os.path.join("/home/", USER)
env.repo              = REPOSITORY
env.branch            = BRANCH
env.project_dir       = os.path.join(env.home, 'webapps', PROJECT_NAME)
env.settings_dir      = os.path.join(env.project_dir, SETTINGS_SUBDIR)
env.supervisor_dir    = os.path.join(env.home, 'webapps', 'supervisor')
env.virtualenv_dir    = VIRTUALENVS
env.virtualenv        = VIRTUALENVS + '/' + env.project
env.supervisor_ve_dir = os.path.join(env.virtualenv_dir, '/supervisor')
env.webfaction        = _WebFactionXmlRPC(USER, PASSWORD)
env.supervisor_cfg    = '%s/conf.d/%s.conf' % (env.supervisor_dir, env.project)
env.mailgun_api_key   = MAILGUN_API_KEY
env.mailgun_sender_domain = MAILGUN_SENDER_DOMAIN
env.mailaddress       = MAILADDRESS
env.broker            = BROKER_URL
env.phantomjs         = PHANTOMJS
env.memcached         = MEMCACHED_SOCKET

env.domain            = "ssfmontreux.ch"
env.subdomains        = ['.',]
env.https             = False
env.website_name      = env.project
env.django_app_name   = env.project
env.static_app_name   = env.project + '_static'
env.static_root       = os.path.join(env.home, 'webapps', env.static_app_name)
env.media_app_name    = env.project + '_media'
env.media_root        = os.path.join(env.home, 'webapps', env.media_app_name)

env.static_root       = os.path.join(env.home, 'webapps', env.static_app_name)
env.allowed_hosts     = [__concat_domain(subdomain, env.domain) for subdomain in env.subdomains]
env.allowed_hosts_str = ';'.join(env.allowed_hosts)

env.memcached_size    = 5
env.nb_workers        = 1
env.nb_web_workers    = 1


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

def _create_media_app():
    print("Creating static app...")
    for app_info in env.webfaction.list_apps():
        if app_info['name'] == env.media_app_name:
            return

    env.webfaction.create_app(env.project + '_media', 'static_only', False, '')


def _create_main_app():
    print("Creating main app...")
    app_name = env.project
    for app_info in env.webfaction.list_apps():
        if app_info['name'] == app_name:
            env.app_port = app_info['port']
            return

    port = env.webfaction.create_app(env.project, 'custom_app_with_port', False, '')


def _create_domain():
    print("Creating domain %s..." % env.domain)
    for (domain_id, domain, subdomains) in env.webfaction.list_domains():
        if domain == env.domain and set(subdomains) == set(env.subdomains):
            print("Domain already exists")
            return
    try:
        env.webfaction.create_domain(env.domain, *env.subdomains)
        print("...done")
    except:
        print('Error creating domain. Continuing.')


def _create_website():
    print("Creating website")
    website_fct = env.webfaction.create_website
    for name_info in env.webfaction.list_websites():
        if name_info.get('name') == env.website_name:
            print("Website already exists")
            website_fct = env.webfaction.update_website


    machines = env.webfaction.list_ips()
    env.ip = None
    for machine in machines:
        if machine.get('machine') == env.machine:
            ip = machine.get('ip')


    website_fct(env.website_name, ip, env.https,
                env.allowed_hosts,
                (env.django_app_name, '/'),
                (env.static_app_name, '/static'),
                (env.media_app_name, '/media'))
    print("...done")


def configure_supervisor():
    print("Configuring supervisor...")
    if not 'secret_key' in env:
        secret_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$^&*(-_=+)'
        env.secretkey = ''.join([random.SystemRandom().choice(secret_chars) for i in range(50)])
    if 'app_port' not in env:
        for app_config in env.webfaction.list_apps():
            if app_config.get('name') == env.project:
                env.app_port = app_config.get('port')
                break
    require('app_port')
    upload_template(os.path.join(env.local_config_dir, 'gunicorn.conf'),
                    env.supervisor_cfg, env)

    reload_supervisor()


def reconf():
    configure_supervisor()
    print("Configuring virtualenv...")
    upload_template(os.path.join(env.local_config_dir, 'postactivate.tpl'),
                    os.path.join(env.virtualenv, 'bin', 'postactivate'),
                    env)


def configure_webfaction():
    _create_db()
    _create_static_app()
    _create_media_app()
    _create_main_app()
    _create_domain()
    _create_website()

def install_app():
    "Installs the django project in its own wf app and virtualenv"
    configure_webfaction()
    with cd(env.project_dir):
        if not exists('sportfac'):
            print("Grabbing sources...")
            run('git clone -b %s %s %s' % (env.branch, env.repo, env.project_dir))

    print("Creating virtualenv...")
    _create_ve(env.project)
    configure_supervisor()

    reload_app()
    restart_app()


def reload_app(arg=None):
    "Pulls app and refreshes requirements"
    with cd(env.project_dir):
        run('git pull origin %s' % env.branch)

    if arg <> "quick":
        with cd(env.project_dir):
            _ve_run(env.project, "pip install -r requirements.txt --upgrade")
            djangoadmin('migrate_schemas')
            djangoadmin('collectstatic --noinput')
            djangoadmin('checkpreferences')
    restart_app()


def reload_supervisor():
    "Reload supervisor config"
    with cd(env.supervisor_dir):
        _ve_run('supervisor','supervisorctl reread && supervisorctl update')

def restart_app():
    "Restarts the app using supervisorctl"
    with cd(env.supervisor_dir):
        _ve_run('supervisor','supervisorctl restart %s' % env.project)
        _ve_run('supervisor','supervisorctl restart %s_worker' % env.project)




### Helper functions

def _create_ve(name):
    """creates virtualenv using virtualenvwrapper
    """
    secret_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$^&*(-_=+)'
    env.secretkey = ''.join([random.SystemRandom().choice(secret_chars) for i in range(50)])

    if not exists(env.virtualenv):
        with cd(env.virtualenv_dir):
            run('mkvirtualenv -p /usr/local/bin/python2.7 --no-site-packages %s' % name)
    else:
        print("Virtualenv with name %s already exists. Skipping.") % name

    env.allowed_hosts = ''
    upload_template(os.path.join(env.local_config_dir, 'postactivate.tpl'),
                    os.path.join(env.virtualenv, 'bin', 'postactivate'),
                    env)
    upload_template(os.path.join(env.local_config_dir, 'virtualenv_project'),
                    os.path.join(env.virtualenv, '.project'),
                    env)



def _ve_run(ve, cmd):
    """virtualenv wrapper for fabric commands"""
    run("""/bin/bash -l -c 'source %s/bin/virtualenvwrapper.sh && workon %s && %s'""" % (env.home, ve, cmd))

def djangoadmin(cmd):
    _ve_run(env.project, "django-admin %s" % cmd)


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
