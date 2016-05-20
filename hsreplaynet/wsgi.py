"""
WSGI config for hsreplayarchive project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""

import os
import sys
from django.core.wsgi import get_wsgi_application
from whitenoise.django import DjangoWhiteNoise

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hsreplaynet.settings")

application = get_wsgi_application()
application = DjangoWhiteNoise(application)
