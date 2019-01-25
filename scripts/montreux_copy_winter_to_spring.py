# -*- coding: utf-8 -*-
from subprocess import Popen, PIPE
from os import path
import os, subprocess

import json

IGNORE_DEFAULT = set(["SHLVL", "PWD", "_"])


def _noscripterror(script_path):
    return IOError("File does not exist: %s" % script_path)


class ShellScriptException(Exception):
    def __init__(self, shell_script, shell_error):
        self.shell_script = shell_script
        self.shell_error = shell_error
        msg = "Error processing script %s: %s" % (shell_script, shell_error)
        Exception.__init__(self, msg)


def list_vars(script_path, ignore=IGNORE_DEFAULT):
    """
    Given a shell script, returns a list of shell variable names.
    Note: this method executes the script, so beware if it contains side-effects.
    :param script_path: Path the a shell script
    :type script_path: str or unicode
    :param ignore: variable names to ignore.  By default we ignore variables
                    that env injects into the script's environment.
                    See IGNORE_DEFAULT.
    :type ignore: iterable
    :return: Key value pairs representing the environment variables defined
            in the script.
    :rtype: list
    """
    if path.isfile(script_path):
        input = (""". "%s"; env | awk -F = '/[a-zA-Z_][a-zA-Z_0-9]*=/ """ % script_path +
                 """{ if (!system("[ -n \\"${" $1 "}\\" ]")) print $1 }'""")
        cmd = "env -i bash".split()

        p = Popen(cmd, stdout=PIPE, stdin=PIPE, stderr=PIPE)
        stdout_data, stderr_data = p.communicate(input=input)
        if stderr_data:
            raise ShellScriptException(script_path, stderr_data)
        else:
            lines = stdout_data.split()
            return [elt for elt in lines if elt not in ignore]
    else:
        raise _noscripterror(script_path)


def get_vars(script_path, ignore=IGNORE_DEFAULT):
    """
    Gets the values of environment variables defined in a shell script.
    Note: this method executes the script potentially many times.
    :param script_path: Path the a shell script
    :type script_path: str or unicode
    :param ignore: variable names to ignore.  By default we ignore variables
                    that env injects into the script's environment.
                    See IGNORE_DEFAULT.
    :type ignore: iterable
    :return: Key value pairs representing the environment variables defined
            in the script.
    :rtype: dict
    """

    # Iterate over every var independently:
    # This is slower than using env, but enables us to capture multiline variables
    return dict((var, get_var(script_path, var)) for var in list_vars(script_path))


def get_var(script_path, var):
    """
    Given a script, and the name of an environment variable, returns the
    value of the environment variable.
    :param script_path: Path the a shell script
    :type script_path: str or unicode
    :param var: environment variable name
    :type var: str or unicode
    :return: str
    """
    if path.isfile(script_path):
        input = '. "%s"; echo -n "$%s"\n'% (script_path, var)
        pipe = Popen(["bash"],  stdout=PIPE, stdin=PIPE, stderr=PIPE)
        stdout_data, stderr_data = pipe.communicate(input=input)
        if stderr_data:
            raise ShellScriptException(script_path, stderr_data)
        else:
            return stdout_data
    else:
        raise _noscripterror(script_path)


PYTHONPATH = '/home/grfavre/.virtualenvs/{}/bin'
PROJECTPATH = '/home/grfavre/webapps/{}'
POSTACTIVATE = PYTHONPATH + '/postactivate'


def run_command(env_name, command, *args):
    env_file = POSTACTIVATE.format(env_name)
    envvars = get_vars(env_file)
    pythonpath = PYTHONPATH.format(env_name)
    p = subprocess.Popen([pythonpath + '/python', 'sportfac/manage.py', command] + list(args),
                         cwd=PROJECTPATH.format(env_name),
                         env=envvars,
                         stdout=subprocess.PIPE)
    out, err = p.communicate()
    return out


def set_env():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sportfac.settings.local")
    import django
    django.setup()


FIELDS_TO_IMPORT = ('country', 'last_name', 'birth_date', 'password',
                    'private_phone', 'private_phone2', 'private_phone3', 'city', 'first_name',
                    'iban', 'address', 'zipcode', 'email',
                    )


def copy_users(source_env):
    set_env()
    users = run_command(source_env, 'dumpdata', 'profiles.familyUser')
    from profiles.models import FamilyUser
    data = json.loads(users)
    all_existing_users = {}
    for user in FamilyUser.objects.all():
        all_existing_users[user.email] = user

    for user in data:
        fields = user['fields']
        user_data = {}
        for field in FIELDS_TO_IMPORT:
            user_data[field] = fields[field]
        if user_data['email'] and user_data['email'] not in all_existing_users:
            FamilyUser.objects.create(**user_data)
            print('Created user: %s' % fields['email'])
        elif user_data['email'] in all_existing_users:
            user.update(**user_data)
            print('Updated user: %s' % fields['email'])


copy_users('sportfac_montreux_ski')