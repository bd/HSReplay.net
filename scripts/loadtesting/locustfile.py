"""
A locust file for load testing the uploader performance.

This file is written for Python 2.7 and requires additional dependencies.
See the locust installation instructions:

http://docs.locust.io/en/latest/installation.html

To run on OS X:
https://github.com/kennethreitz/requests/issues/2022

Each locust is configured to have an AVERAGE_WAIT of 1 second before
triggering the next task. To calculate the amount of load to be generated,
you must know the average lambda execution duration. The hatch rate should
be set to the number of requests per second you want to hit the lambda end
point. The number of locust should be calculated as follows:

NUM_LOCUSTS = HATCH_RATE * (AVERAGE_WAIT + AVG_LAMDA_DURATION)

For example, let's assume that we want to generate 3 uploads / second and
lambda is currently taking around 20 seconds on average to process an upload.
In that case we must have 3 * (1 + 20) or 63 locusts and a hatch rate of 3.
When the test starts, every second 3 locusts will hatch and each initiate a
request shortly after hatching. Thus achieving the desired load level almost
immediately. This will be maintained for 21 seconds as 3 new locusts get
hatched each second.
After 21 seconds the test will stop hatching new locust, however the first
wave of hatched locust should all be completing at this point and initiating
their second round of requests, thus maintaining the load at the target rate
of 3 uploads / second.

NOTE: Both the web console and the stats printed to the console will provide
you with the actual requests / second rate that has been achieved. Once you
have a baseline, you can tune the numbers to zero in on your target rate.

To initiate a load test against hsreplay.net locally, use the following
command from within this directory:

$ locust --host=https://localhost:8000 --print-stats

Then open the web console to start the test: http://127.0.0.1:8089

When this is run headlessly by Jenkins it can be executed via the following command:

$ locust --host=https://upload.hsreplay.net --no-web
  --clients=63 --hatch-rate=3 --num-request=189 --print-stats

--num-request tells the test when to shutdown and report back to Jenkins.
Setting it to 3 * NUM_LOCUSTS, ensures the test achieves a steady state
before it exits.

--print-stats is optional but provides more useful debugging info to the console.
"""
import os
import patch_gevent
from locust import HttpLocust, ResponseError, TaskSet, task


BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
DATA_DIR = os.path.join(BASE_DIR, "data", "hsreplay-test-data")

SHORT_REPLAY = open(os.path.join(DATA_DIR, "examples", "short.log")).read()  # 4 minute game
MEDIUM_REPLAY = open(os.path.join(DATA_DIR, "examples", "medium.log")).read()  # 9 minute game
LARGE_REPLAY = open(os.path.join(DATA_DIR, "examples", "large.log")).read()  # 31 minute game


class UploadBehavior(TaskSet):
	def on_start(self):
		"""
		Called when a Locust start before any task is scheduled
		"""
		# This is where we request an UploadToken for this user.
		self.api_key = os.environ.get("API_KEY")
		if not self.api_key:
			raise RuntimeError("The API_KEY environment variable needs to be set.")

		self.is_live = self.client.base_url == "https://upload.hsreplay.net"
		self.api_token_url = "/api/v1/tokens/"
		if self.is_live:
			self.api_token_url = "https://hsreplay.net" + self.api_token_url
			self.api_endpoint = "/api/v1/replay/upload/powerlog"
		else:
			self.api_endpoint = "/api/v1/uploads/"

		self.token = self.request_upload_token()

	def request_upload_token(self):
		headers = {"X-Api-Key": self.api_key}
		with self.client.post(self.api_token_url, headers=headers, catch_response=True) as response:
			data = response.json()
			if "key" not in data:
				raise ResponseError("Could not request a new upload token")
			return data["key"]

	def post_replay(self, name, data):
		kwargs = {
			"data": {
				"match_start": "2016-05-10T17:10:06.4923855+02:00",
				"build": 12574,
			},
			"headers": {
				"Authorization": "Token %s" % (self.token),
				"X-Api-Key": self.api_key,
			},
			"timeout": None,
			"name": name,
		}

		if self.is_live:
			# On production systems, the replay file is the data
			kwargs["params"] = kwargs.pop("data")
			kwargs["data"] = data
		else:
			# By default, the replay file is the `file` parameter
			kwargs["files"] = {"file": (name + ".log", data)}
			kwargs["data"]["type"] = 1

		return self.client.post(self.api_endpoint, **kwargs)

	@task(6)
	def short_replay(self):
		self.post_replay("short_replay", SHORT_REPLAY)

	@task(2)
	def medium_replay(self):
		self.post_replay("medium_replay", MEDIUM_REPLAY)

	@task(1)
	def large_replay(self):
		self.post_replay("large_replay", LARGE_REPLAY)


class ReplayUploadClient(HttpLocust):
	task_set = UploadBehavior
	# The amount of time each client waits between
	# upload is randomly between the min and max range.
	min_wait = 0 # 0 Seconds
	max_wait = 2000 # 2 Seconds
