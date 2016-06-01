from fabric.api import run, sudo
from fabric.contrib.files import exists


REPO_URL = "https://github.com/amw2104/hsreplaynet"
NO_PIP_CACHE = True


def deploy():
	site_folder = "/srv/http/hsreplay.net"
	source_folder = site_folder + "/source"
	venv = site_folder + "/virtualenv"

	sudo("mkdir -p %s" % (source_folder), user="www-data")

	_get_latest_source(source_folder)
	_update_virtualenv(venv, source_folder + "/requirements.txt")
	_update_static_files(venv, source_folder)
	_update_database(venv, source_folder)

	_restart_web_server()


def _get_latest_source(path):
	if exists(path + "/.git"):
		sudo("git -C %s fetch" % (path), user="www-data")
	else:
		sudo("git clone %s %s" % (REPO_URL, path), user="www-data")
	current_commit = run("git -C %s rev-parse origin/master" % (path))
	sudo("git -C %s reset --hard %s" % (path, current_commit), user="www-data")


def _update_virtualenv(venv, requirements):
	if not exists(venv + "/bin/pip"):
		sudo("python3 -m venv %s" % (venv), user="www-data")

	command = "%s/bin/pip install -r %s" % (venv, requirements)
	if NO_PIP_CACHE:
		command += " --no-cache-dir"
	sudo(command, user="www-data")


def _update_static_files(venv, path):
	if not exists(path + "/hsreplaynet/web/static/bootstrap"):
		sudo(path + "/get_bootstrap.sh", user="www-data")
	sudo("%s/bin/python %s/manage.py collectstatic --noinput" % (venv, path), user="www-data")


def _update_database(venv, path):
	sudo("%s/bin/python %s/manage.py migrate --noinput" % (venv, path), user="www-data")


def _restart_web_server():
	sudo("supervisorctl restart hsreplay.net")
