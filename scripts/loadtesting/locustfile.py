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

$ locust --host=https://upload.hsreplay.net --print-stats

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
import requests
import patch_gevent
from locust import HttpLocust, TaskSet, task

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
DATA_DIR = os.path.join(BASE_DIR, "data", "hsreplay-test-data")

SHORT_REPLAY = open(os.path.join(DATA_DIR, "examples", "short.log")).read()  # 4 minute game
MEDIUM_REPLAY = open(os.path.join(DATA_DIR, "examples", "medium.log")).read()  # 9 minute game
LARGE_REPLAY = open(os.path.join(DATA_DIR, "examples", "large.log")).read()  # 31 minute game

API_KEY = os.environ.get("API_KEY")
API_ENDPOINT = "/api/v1/replay/upload/raw"


class UploadBehavior(TaskSet):
	def on_start(self):
		"""
		Called when a Locust start before any task is scheduled
		"""
		# This is where we request an UploadToken for this user.
		if not API_KEY:
			raise RuntimeError("The API_KEY environment variable needs to be set.")
		self.HEADERS = {
			"x-hsreplay-api-key": API_KEY,
			"x-hsreplay-upload-token": self.request_new_upload_token(),
		}
		self.QUERY_PARAMS = {
			#"player_1_rank" : 18,
			#"match_start_timestamp" : "2016-05-10T17:10:06.4923855+02:00"
		}

	def request_new_upload_token(self):
		response = requests.post("https://hsreplay.net/api/v1/tokens/", {"api_key": API_KEY})
		return response.json()["key"].encode("ascii")

	@task(6)
	def short_replay(self):
		# We attempt to upload a short replay
		self.client.post(API_ENDPOINT,
			data=SHORT_REPLAY,
			params=self.QUERY_PARAMS,
			headers=self.HEADERS,
			timeout=None,
			name="short_replay"
		)

	@task(2)
	def medium_replay(self):
		# We upload medium length replays twice as often as short ones or long ones.
		self.client.post(API_ENDPOINT,
			data=MEDIUM_REPLAY,
			params=self.QUERY_PARAMS,
			headers=self.HEADERS,
			timeout=None,
			name="medium_replay"
		)

	@task(1)
	def long_replay(self):
		# We upload a long replay
		self.client.post(API_ENDPOINT,
			data=LARGE_REPLAY,
			params=self.QUERY_PARAMS,
			headers=self.HEADERS,
			timeout=None,
			name="long_replay"
		)


class ReplayUploadClient(HttpLocust):
	task_set = UploadBehavior
	# The amount of time each client waits between
	# upload is randomly between the min and max range.
	min_wait = 0 # 0 Seconds
	max_wait = 2000 # 2 Seconds
