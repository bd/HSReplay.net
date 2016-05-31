import time
from contextlib import contextmanager
from django.conf import settings
from django.utils.timezone import now
from influxdb import InfluxDBClient
from .utils import logger

if "raven.contrib.django.raven_compat" in settings.INSTALLED_APPS:
	from raven.contrib.django.raven_compat.models import client as sentry
else:
	sentry = None


def error_handler(e):
	if sentry is not None:
		sentry.captureException()
	else:
		logger.exception(e)


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
