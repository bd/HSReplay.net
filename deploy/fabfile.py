import os
from fabric.api import run, sudo
from fabric.contrib.files import exists
from fabric.context_managers import shell_env


REPO_URL = "https://github.com/amw2104/hsreplaynet"
NO_PIP_CACHE = True


def deploy():
	site_folder = "/srv/http/hsreplay.net"
	source_folder = site_folder + "/source"
	_get_latest_source(source_folder)
	_create_directory_structure_if_necessary(site_folder)
	_update_virtualenv(source_folder)
	_update_static_files(source_folder)
	_update_database(source_folder)
	_restart_web_server()


def _create_directory_structure_if_necessary(site_folder):
	sudo("mkdir -p %s/source" % (site_folder,), user="www-data")
	sudo("mkdir -p %s/source/virtualenv" % (site_folder,), user="www-data")


def _get_latest_source(source_folder):
	if exists(source_folder + "/.git"):
		sudo("cd %s && git fetch" % (source_folder), user="www-data")
	else:
		sudo("git clone %s %s" % (REPO_URL, source_folder), user="www-data")
	current_commit = run("git -C %s rev-parse origin/master" % (source_folder))
	sudo("cd %s && git reset --hard %s" % (source_folder, current_commit), user="www-data")


def _update_virtualenv(source_folder):
	virtualenv_folder = source_folder + "/virtualenv"
	if not exists(virtualenv_folder + "/bin/pip"):
		sudo("python3 -m venv %s" % (virtualenv_folder), user="www-data")

	command = "%s/bin/pip install -r %s/requirements.txt" % (virtualenv_folder, source_folder)
	if NO_PIP_CACHE:
		command += " --no-cache-dir"
	sudo(command, user="www-data")


def _update_static_files(source_folder):
	sudo("cd %s/hsreplaynet && ../virtualenv/bin/python manage.py collectstatic --noinput" % (source_folder,), user="www-data")


def _update_database(source_folder):
	with shell_env(
		HSREPLAYNET_DB_USER=os.environ.get("HSREPLAYNET_DB_USER"),
		HSREPLAYNET_DB_PASSWORD=os.environ.get("HSREPLAYNET_DB_PASSWORD"),
		HSREPLAYNET_DB_HOST=os.environ.get("HSREPLAYNET_DB_HOST"),
		HSREPLAYNET_DB_PORT=os.environ.get("HSREPLAYNET_DB_PORT")
	):
		sudo("cd %s/hsreplaynet && ../virtualenv/bin/python manage.py migrate --noinput" % (source_folder,), user="www-data")


def _restart_web_server():
	sudo("supervisorctl restart hsreplay.net")
