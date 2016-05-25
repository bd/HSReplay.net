import os
from fabric.api import run, sudo
from fabric.contrib.files import exists
from fabric.context_managers import shell_env


REPO_URL = "https://github.com/amw2104/hsreplaynet"
NO_PIP_CACHE = True


def deploy():
	site_folder = "/srv/http/hsreplay.net"
	source_folder = site_folder + "/source"
	app_folder = source_folder + "/hsreplaynet"
	venv = site_folder + "/virtualenv"

	sudo("mkdir -p %s" % (source_folder), user="www-data")

	_get_latest_source(source_folder)
	_update_virtualenv(venv, source_folder + "/requirements.txt")
	_update_static_files(venv, app_folder)
	_update_database(venv, app_folder)

	_restart_web_server()


def _get_latest_source(source_folder):
	if exists(source_folder + "/.git"):
		sudo("git -C %s fetch" % (source_folder), user="www-data")
	else:
		sudo("git clone %s %s" % (REPO_URL, source_folder), user="www-data")
	current_commit = run("git -C %s rev-parse origin/master" % (source_folder))
	sudo("git -C %s reset --hard %s" % (source_folder, current_commit), user="www-data")


def _update_virtualenv(venv, requirements):
	if not exists(venv + "/bin/pip"):
		sudo("python3 -m venv %s" % (venv), user="www-data")

	command = "%s/bin/pip install -r %s" % (venv, requirements)
	if NO_PIP_CACHE:
		command += " --no-cache-dir"
	sudo(command, user="www-data")


def _update_static_files(venv, app_folder):
	sudo("%s/bin/python %s/manage.py collectstatic --noinput" % (venv, app_folder), user="www-data")


def _update_database(venv, app_folder):
	sudo("%s/bin/python %s/manage.py migrate --noinput" % (venv, app_folder), user="www-data")


def _restart_web_server():
	sudo("supervisorctl restart hsreplay.net")
