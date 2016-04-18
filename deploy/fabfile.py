from fabric.contrib.files import append, exists, sed
from fabric.api import env, local, run, sudo
import random, time
from fabric.context_managers import shell_env
import os

REPO_URL = 'https://github.com/amw2104/hsreplaynet'

def deploy():
    site_folder = '/srv/http/hsreplay.net'
    source_folder = site_folder + '/source'
    _get_latest_source(source_folder)
    _create_directory_structure_if_necessary(site_folder)
    _update_settings(source_folder, 'hsreplay.net')
    _update_virtualenv(source_folder)
    _update_static_files(source_folder)
    _update_database(source_folder)
    _restart_web_server()


def _create_directory_structure_if_necessary(site_folder):
    sudo('mkdir -p %s/source' % (site_folder,), user='www-data')
    sudo('mkdir -p %s/source/virtualenv' % (site_folder,), user='www-data')


def _get_latest_source(source_folder):
    if exists(source_folder + '/.git'):
        sudo('cd %s && git fetch' % (source_folder,), user='www-data')
    else:
        sudo('git clone %s %s' % (REPO_URL, source_folder), user='www-data')
    current_commit = local("git log -n 1 --format=%H", capture=True)
    sudo('cd %s && git reset --hard %s' % (source_folder, current_commit), user='www-data')


def _update_settings(source_folder, site_name):
    settings_path = source_folder + '/hsreplaynet/config/settings.py'
    sed(settings_path, "DEBUG = True", "DEBUG = False", use_sudo=True)
    sed(settings_path, 'ALLOWED_HOSTS =.+$', 'ALLOWED_HOSTS = ["%s", "www.%s"]' % (site_name,site_name), use_sudo=True)
    secret_key_file = source_folder + '/hsreplaynet/config/secret_key.py'
    if not exists(secret_key_file):
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
        key = ''.join(random.SystemRandom().choice(chars) for _ in range(50))
        append(secret_key_file, "SECRET_KEY = '%s'" % (key,), use_sudo=True)
    append(settings_path, '\nfrom .secret_key import SECRET_KEY', use_sudo=True)


def _update_virtualenv(source_folder):
    virtualenv_folder = source_folder + '/virtualenv'
    if not exists(virtualenv_folder + '/bin/pip'):
        sudo('virtualenv --python=python3 %s' % (virtualenv_folder,), user='www-data')
    sudo('%s/bin/pip install -r %s/requirements.txt' % (virtualenv_folder, source_folder), user='www-data')


def _update_static_files(source_folder):
    sudo('cd %s/hsreplaynet && ../virtualenv/bin/python manage.py collectstatic --noinput' % (source_folder,), user='www-data')


def _update_database(source_folder):
    with shell_env(HSREPLAYNET_DB_USER=os.environ.get('HSREPLAYNET_DB_USER'),
                   HSREPLAYNET_DB_PASSWORD=os.environ.get('HSREPLAYNET_DB_PASSWORD'),
                   HSREPLAYNET_DB_HOST=os.environ.get('HSREPLAYNET_DB_HOST'),
                   HSREPLAYNET_DB_PORT=os.environ.get('HSREPLAYNET_DB_PORT')):

        sudo('cd %s/hsreplaynet && ../virtualenv/bin/python manage.py migrate --noinput' % (source_folder,), user='www-data')


def _restart_web_server():
    sudo('restart gunicorn-hsreplay.net', user='www-data')
