import time
from contextlib import contextmanager
from django.conf import settings
from django.utils.timezone import now
from influxdb import InfluxDBClient
from .utils import logger
from functools import wraps

if "raven.contrib.django.raven_compat" in settings.INSTALLED_APPS:
	from raven.contrib.django.raven_compat.models import client as sentry
else:
	sentry = None


def error_handler(e):
	if sentry is not None:
		sentry.captureException()
	else:
		logger.exception(e)


def sentry_aware_handler(func):
	"""A wrapper which should be used around all handlers in the lambdas module to ensure sentry reporting."""
	@wraps(func)
	def wrapper(*args, **kwargs):
		if len(args) != 2:
			msg = "@sentry_aware_handler must wrap functions with two arguments. E.g. handler(event, context)"
			raise ValueError(msg)

		context = args[1]
		if not hasattr(context, "log_group_name"):
			msg = "@sentry_aware_handler has been used with a function whose second argument is not a context object."
			raise ValueError(msg)

		if sentry:
			# Provide additional metadata to sentry in case the exception gets trapped and reported within the function.
			sentry.user_context({
				"aws_log_group_name": getattr(context, "log_group_name"),
				"aws_log_stream_name": getattr(context, "log_stream_name"),
				"aws_function_name": getattr(context, "function_name")
			})

		try:
			return func(*args, **kwargs)
		except Exception as e:
			error_handler(e)
	return wrapper


influx = InfluxDBClient(
	settings.INFLUX_DB_ADDRESS,
	8086,
	username=settings.INFLUX_DB_USER,
	password=settings.INFLUX_DB_PASSWORD,
	database=settings.INFLUX_DB_NAME
)

def influx_metric(measure, fields, timestamp=None, tags={}):
	if timestamp is None:
		timestamp = now()
	if settings.IS_RUNNING_LIVE or settings.IS_RUNNING_AS_LAMBDA:
		payload = {
			"measurement": measure,
			"tags": tags,
			"fields": fields,
		}

		payload["time"] = timestamp.isoformat()
		logger.info("About To Send Metric To InfluxDB: %s" % str(payload))
		influx.write_points([payload])


@contextmanager
def influx_timer(measure, timestamp=None, **kwargs):
	"""
	Reports the duration of the context manager.
	Additional kwargs are passed to InfluxDB as tags.
	"""
	start_time = time.clock()
	exception_raised_in_with_block = False
	if timestamp is None:
		timestamp = now()
	try:
		yield
	except Exception as e:
		exception_raised_in_with_block = True
		raise e
	finally:
		stop_time = time.clock()
		duration = (stop_time - start_time) * 10000

		if settings.IS_RUNNING_LIVE or settings.IS_RUNNING_AS_LAMBDA:
			tags = kwargs
			tags["exception_thrown"] = exception_raised_in_with_block
			payload = {
				"measurement": measure,
				"tags": tags,
				"fields": {
					"value": duration,
				}
			}

			payload["time"] = timestamp.isoformat()
			logger.info("About To Send Metric To InfluxDB: %s" % (str(payload)))
			influx.write_points([payload])
