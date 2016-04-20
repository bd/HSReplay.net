""" A module providing entry points for AWS Lambda.

This module and all its dependencies will be interpreted under Python 2.7 and must be compatible.
"""
import pymysql
pymysql.install_as_MySQLdb()
import os, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from hsreplaynet.web.models import HSReplaySingleGameFileUpload

def django_models_test(event, context):
	return str(HSReplaySingleGameFileUpload.objects.count())
