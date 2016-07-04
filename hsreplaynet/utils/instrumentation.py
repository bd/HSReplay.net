import time, os
from contextlib import contextmanager
from functools import wraps
from django.conf import settings
from django.utils.timezone import now
from . import logger


if "raven.contrib.django.raven_compat" in settings.INSTALLED_APPS:
	from raven.contrib.django.raven_compat.models import client as sentry
else:
	sentry = None


def error_handler(e):
	if sentry is not None:
		sentry.captureException()
	else:
		logger.exception(e)


def lambda_handler(func):
	"""Indicates the decorated function is a AWS Lambda handler.

	The following standard lifecycle services are provided:
		- Sentry reporting for all Exceptions that propagate
		- Capturing a standard set of metrics for Influx
		- Making sure all connections to the DB are closed
	"""
	@wraps(func)
	def wrapper(*args, **kwargs):
		if len(args) != 2:
			msg = "@lambda_handler must wrap functions with two arguments. E.g. handler(event, context)"
			raise ValueError(msg)

		context = args[1]
		if not hasattr(context, "log_group_name"):
			msg = "@lambda_handler has been used with a function whose second argument is not a context object."
			raise ValueError(msg)


		if sentry:
			# Provide additional metadata to sentry in case the exception gets trapped and reported within the function.
			sentry.user_context({
				"aws_log_group_name": getattr(context, "log_group_name"),
				"aws_log_stream_name": getattr(context, "log_stream_name"),
				"aws_function_name": getattr(context, "function_name")
			})

		try:

			measurement = func.__name__
			with influx_gauge(measurement):
				return func(*args, **kwargs)

		except Exception as e:
			logger.exception("Got an exception: %r", e)
			if sentry:
				logger.info("Inside sentry capture block.")
				sentry.captureException()
			else:
				logger.info("Sentry is not available.")
			raise
		finally:
			from django.db import connection
			connection.close()

	return wrapper



try:
	if settings.IS_RUNNING_LIVE or settings.IS_RUNNING_AS_LAMBDA:
		from influxdb import InfluxDBClient

		influx_settings = settings.INFLUX_DATABASES["hsreplaynet"]
		influx = InfluxDBClient(
			host=influx_settings["HOST"],
			port=influx_settings.get("PORT", 8086),
			username=influx_settings["USER"],
			password=influx_settings["PASSWORD"],
			database=influx_settings["NAME"],
			ssl=influx_settings.get("SSL", False),
		)
	else:
		influx = None
except ImportError as e:
	logger.info("Influx is not installed, so will be disabled (%s)", e)
	influx = None



@contextmanager
def influx_gauge(measure, timestamp=None, **kwargs):
	"""
	Gauges measure the count of inflight uploads.
	Additional kwargs are passed to InfluxDB as tags.
	"""
	exception_raised = False
	influx_metric(measure, fields={"count": 1}, timestamp=timestamp, **kwargs)
	try:
		yield
	except Exception:
		exception_raised = True
		raise
	finally:
		kwargs["exception_thrown"] = exception_raised
		influx_metric(measure, fields={"count": -1}, timestamp=timestamp, **kwargs)


def influx_write_payload(payload):
	try:
		influx.write_points(payload)
	except Exception as e:
		# Can happen if Influx if not available for example
		error_handler(e)


def influx_metric(measure, fields, timestamp=None, **kwargs):
	if influx is None:
		return
	if timestamp is None:
		timestamp = now()
	if settings.IS_RUNNING_LIVE or settings.IS_RUNNING_AS_LAMBDA:
		payload = {
			"measurement": measure,
			"tags": kwargs,
			"fields": fields,
		}

		payload["time"] = timestamp.isoformat()
		influx_write_payload([payload])


@contextmanager
def influx_timer(measure, timestamp=None, **kwargs):
	"""
	Reports the duration of the context manager.
	Additional kwargs are passed to InfluxDB as tags.
	"""
	if influx is None:
		return
	start_time = time.clock()
	exception_raised = False
	if timestamp is None:
		timestamp = now()
	try:
		yield
	except Exception:
		exception_raised = True
		raise
	finally:
		stop_time = time.clock()
		duration = (stop_time - start_time) * 10000

		tags = kwargs
		tags["exception_thrown"] = exception_raised
		payload = {
			"measurement": measure,
			"tags": tags,
			"fields": {
				"value": duration,
			}
		}

		payload["time"] = timestamp.isoformat()
		influx_write_payload([payload])
