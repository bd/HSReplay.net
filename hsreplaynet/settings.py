"""
Django settings for hsreplay.net project.
"""

import os
from django.core.urlresolvers import reverse_lazy

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IS_RUNNING_AS_LAMBDA = bool(os.environ.get("IS_RUNNING_AS_LAMBDA", ""))
IS_RUNNING_LIVE = os.uname()[1] == "hearthsim.net"

ROOT_URLCONF = "hsreplaynet.urls"
WSGI_APPLICATION = "hsreplaynet.wsgi.application"

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "be8^qa&f2fut7_1%q@x2%nkw5u=-r6-rwj8c^+)5m-6e^!zags"

if IS_RUNNING_LIVE or IS_RUNNING_AS_LAMBDA:
	ALLOWED_HOSTS = ["hsreplay.net", "www.hsreplay.net"]
	DEBUG = False
else:
	# SECURITY WARNING: don't run with debug turned on in production!
	DEBUG = True
	ALLOWED_HOSTS = []


INSTALLED_APPS = (
	"django.contrib.admin",
	"django.contrib.auth",
	"django.contrib.contenttypes",
	"django.contrib.sessions",
	"django.contrib.messages",
	"django.contrib.staticfiles",
	"django.contrib.sites",
	"rest_framework",
	"hsreplaynet.accounts",
	"hsreplaynet.api",
	"hsreplaynet.web",
	"hsreplaynet.cards",
	"hsreplaynet.lambdas",
)

if not IS_RUNNING_AS_LAMBDA:
	INSTALLED_APPS += (
		"django.contrib.flatpages",
		"allauth",
		"allauth.account",
		"allauth.socialaccount",
		"allauth_battlenet",
	)

MIDDLEWARE_CLASSES = (
	"django.contrib.sessions.middleware.SessionMiddleware",
	"django.middleware.common.CommonMiddleware",
	"django.middleware.csrf.CsrfViewMiddleware",
	"django.contrib.auth.middleware.AuthenticationMiddleware",
	"django.contrib.auth.middleware.SessionAuthenticationMiddleware",
	"django.contrib.messages.middleware.MessageMiddleware",
	"django.middleware.clickjacking.XFrameOptionsMiddleware",
	"django.middleware.security.SecurityMiddleware",
	"django.middleware.gzip.GZipMiddleware",
)

TEMPLATES = [{
	"BACKEND": "django.template.backends.django.DjangoTemplates",
	"DIRS": [
		os.path.join(BASE_DIR, "hsreplaynet", "templates")
	],
	"APP_DIRS": True,
	"OPTIONS": {
		"context_processors": [
			"django.template.context_processors.debug",
			"django.template.context_processors.request",
			"django.contrib.auth.context_processors.auth",
			"django.contrib.messages.context_processors.messages",
		],
	},
}]


# Tests

TEST_RUNNER = "django_nose.NoseTestSuiteRunner"
FIXTURE_DIRS = (os.path.join(BASE_DIR, "hsreplaynet", "test", "fixtures"), )


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, "hsreplaynet", "static")
if DEBUG:
	DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
	STATIC_URL = "/static/"
else:
	DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
	STATICFILES_STORAGE = "whitenoise.django.GzipManifestStaticFilesStorage"
	STATIC_URL = "//static.hsreplay.net/static/"

	# S3
	S3_RAW_LOG_STORAGE_BUCKET = os.environ.get(
		"S3_RAW_LOG_STORAGE_BUCKET",
		"test.raw.replaystorage.hsreplay.net"
	)
	S3_REPLAY_STORAGE_BUCKET = os.environ.get(
		"S3_REPLAY_STORAGE_BUCKET",
		"test.replaystorage.hsreplay.net"
	)
	AWS_STORAGE_BUCKET_NAME = S3_REPLAY_STORAGE_BUCKET

	AWS_S3_USE_SSL = True
	AWS_DEFAULT_ACL = "private"

	AWS_IS_GZIPPED = True
	GZIP_CONTENT_TYPES = (
		"text/xml",
		"text/plain",
		"application/xml",
		"application/octet-stream",
	)

JOUST_STATIC_URL = STATIC_URL + "joust/"
HEARTHSTONEJSON_URL = "https://api.hearthstonejson.com/v1/%(build)s/%(locale)s/cards.json"


# Email
# https://docs.djangoproject.com/en/1.9/ref/settings/#email-backend

SERVER_EMAIL = "admin@hsreplay.net"
DEFAULT_FROM_EMAIL = "contact@hsreplay.net"
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

DATABASES = {
	"default": {
		"ENGINE": "django.db.backends.sqlite3",
		"NAME": os.path.join(BASE_DIR, "hsreplay.db"),
		"USER": "",
		"PASSWORD": "",
		"HOST": "",
		"PORT": "",
	}
}


# Logging

if not IS_RUNNING_AS_LAMBDA:
	# When we are running on Lambda the logging is configured by the runtime
	# to write to CloudWatch so this is not needed.
	LOG_ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, "logs"))

	if not os.path.exists(LOG_ROOT_DIR):
		os.mkdir(LOG_ROOT_DIR)

	LOGGING = {
		"version": 1,
		"disable_existing_loggers": False,
		"formatters": {
			"verbose": {
				"format": "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
				"datefmt": "%d/%b/%Y %H:%M:%S"
			},
		},
		"handlers": {
			"joust": {
				"level": "DEBUG",
				"class": "logging.handlers.RotatingFileHandler",
				"filename": os.path.join(LOG_ROOT_DIR, "joust.log"),
				"maxBytes": 5242880,
				"backupCount": 5,
				"formatter": "verbose"
			},
			"timing": {
				"level": "DEBUG",
				"class": "logging.handlers.RotatingFileHandler",
				"filename": os.path.join(LOG_ROOT_DIR, "timing.log"),
				"maxBytes": 5242880,
				"backupCount": 5,
				"formatter": "verbose"
			},
			"web": {
				"level": "DEBUG",
				"class": "logging.handlers.RotatingFileHandler",
				"filename": os.path.join(LOG_ROOT_DIR, "web.log"),
				"maxBytes": 5242880,
				"backupCount": 5,
				"formatter": "verbose"
			},
			"django_file": {
				"level": "DEBUG",
				"class": "logging.handlers.RotatingFileHandler",
				"filename": os.path.join(LOG_ROOT_DIR, "django.log"),
				"maxBytes": 5242880,
				"backupCount": 5,
				"formatter": "verbose"
			},
			"error_file": {
				"level": "ERROR",
				"class": "logging.handlers.RotatingFileHandler",
				"filename": os.path.join(LOG_ROOT_DIR, "error.log"),
				"maxBytes": 5242880,
				"backupCount": 5,
				"formatter": "verbose"
			},
			"battlenet": {
				"level": "DEBUG",
				"class": "logging.handlers.RotatingFileHandler",
				"filename": os.path.join(LOG_ROOT_DIR, "battlenet.log"),
				"maxBytes": 5242880,
				"backupCount": 5,
				"formatter": "verbose"
			},
		},
		"loggers": {
			"django": {
				"handlers": ["django_file", "error_file"],
				"propagate": True,
				"level": "INFO",
			},
			"TIMING": {
				"handlers": ["timing"],
				"propagate": True,
				"level": "INFO",
			},
			"joust": {
				"handlers": ["joust", "error_file"],
				"propagate": False,
				"level": "DEBUG",
			},
			"web": {
				"handlers": ["web", "error_file"],
				"propagate": False,
				"level": "DEBUG",
			},
		}
	}


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

USE_I18N = True
USE_L10N = True
LANGUAGE_CODE = "en-us"

USE_TZ = True
TIME_ZONE = "UTC"

SITE_ID = 1


# Account settings

AUTHENTICATION_BACKENDS = (
	# Needed to login by username in Django admin, regardless of `allauth`
	"django.contrib.auth.backends.ModelBackend",
	# `allauth` specific authentication methods, such as login by e-mail
	"allauth.account.auth_backends.AuthenticationBackend",
)

LOGIN_REDIRECT_URL = reverse_lazy("my_replays")
LOGIN_URL = reverse_lazy("account_login")

ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http" if DEBUG else "https"
SOCIALACCOUNT_ADAPTER = "allauth_battlenet.provider.BattleNetSocialAccountAdapter"
SOCIALACCOUNT_PROVIDERS = {"battlenet": {"SCOPE": []}}


# API
REST_FRAMEWORK = {
	# Use Django's standard `django.contrib.auth` permissions,
	# or allow read-only access for unauthenticated users.
	"DEFAULT_PERMISSION_CLASSES": [
		"rest_framework.permissions.IsAuthenticatedOrReadOnly",
	]
}


# Custom site settings

API_KEY_HEADER = "x-hsreplay-api-key"
UPLOAD_TOKEN_HEADER = "x-hsreplay-upload-token"


try:
	from hsreplaynet.local_settings import *
except ImportError:
	pass
