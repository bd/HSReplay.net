# [HSReplay.net](https://hsreplay.net)

A website to upload and share your Hearthstone an amazing games.


## Technology overview

The full backend stack is written in Python 3.

* Web framework: [Django](https://www.djangoproject.com/)
* Replay viewer: [Joust](https://github.com/HearthSim/joust/)
* HSReplay implementation: [HSReplay](https://github.com/HearthSim/hsreplay)
* Hearthstone library: [python-hearthstone](https://github.com/HearthSim/python-hearthstone)


### Django libraries

* API: [Django REST Framework](http://www.django-rest-framework.org/)
* Authentication: [Django Allauth](https://github.com/pennersr/django-allauth)
* Storage backends: [Django-Storages](https://github.com/jschneier/django-storages)
* Short IDs: [ShortUUID](https://github.com/stochastic-technologies/shortuuid)


### Production stack

* Accounts: [Battle.net API](https://dev.battle.net/)
* Web server: [nginx](https://nginx.org/)
* App server: [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/)
* Database: [PostgreSQL (RDS)](https://aws.amazon.com/rds/postgresql/)
* Hosting: [Amazon Web Services](https://aws.amazon.com/)
* Analytics: [InfluxDB](https://influxdata.com/)
* Exception tracking: [Sentry](https://getsentry.com/)
* CI: [Jenkins](https://jenkins.io/)

Replays are processed on [Amazon Lambda](https://aws.amazon.com/lambda/details/)
using the Python 2.7 runtime.


## File Installation

Install development dependencies with `pip install -r requirements/dev.txt`.

Settings are present in the `hsreplaynet/settings.py` file. You may copy the
`local_settings.example.py` file to `hsreplaynet/local_settings.py` to
customize settings without modifying the versioned file. This is especially
useful to store sensitive settings such as API keys.
Several settings such as Sentry, Influx and S3 are disabled by default. The
default database engine is set to sqlite3.

Run the dev server with `./manage.py runserver [host:port]`. Will run on
`localhost:8000` by default.

The API is available at `/api/v1/` and is browsable using the DRF interface.


## License

Copyright © HearthSim - All Rights Reserved
