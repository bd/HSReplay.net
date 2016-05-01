#!/bin/bash
source /srv/http/hsreplay.net/source/virtualenv/bin/activate
source /srv/http/hsreplay.net/source/bin/set_production_environment_vars.sh
python /srv/http/hsreplay.net/source/hsreplaynet/manage.py load_cards
