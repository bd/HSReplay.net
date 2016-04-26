""" A module providing entry points for AWS Lambda.

This module and all its dependencies will be interpreted under Python 2.7 and must be compatible. They should provide
mediation between the AWS Lambda interface and standard Django requests.

"""
import pymysql
pymysql.install_as_MySQLdb()
import os, django

#This block properly bootstraps Django for running inside the AWS Lambda Runtime.
os.environ.setdefault('IS_RUNNING_AS_LAMBDA', 'True')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from web.models import HSReplaySingleGameFileUpload



def django_models_test(event, context):
	return str(HSReplaySingleGameFileUpload.objects.count())

if __name__ == '__main__':
	print(django_models_test(None, None))