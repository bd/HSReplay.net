import json
from base64 import b64encode
from hsreplaynet.test.base import (
	TestDataConsumerMixin, CardDataBaseTest, create_agent_and_token
)
from hsreplaynet.web.models import GameReplayUpload
from ..uploads import raw_log_upload_handler, create_power_log_upload_event_handler
from hsreplaynet.uploads.models import GameUpload


class TestRawLogUploadHandler(CardDataBaseTest, TestDataConsumerMixin):
	def setUp(self):
		super(TestRawLogUploadHandler, self).setUp()
		self.agent, self.token = create_agent_and_token()

	def test_all_upload_event_handler(self):
		for descriptor, raw_log, test_uuid in self.get_raw_log_integration_fixtures():
			if descriptor["skip"].lower() == "false":
				# Finish preparing the event object...
				event = descriptor["event"]
				event["body"] = b64encode(raw_log.encode("utf-8"))
				event["headers"]["HTTP_AUTHORIZATION"] = "Token %s" % str(self.token)
				context = descriptor["context"]

				result = create_power_log_upload_event_handler(event, context)

				if descriptor["expected_response_is_replay_id"].lower() == "true":
					self.assertEqual(result["result_type"], "SUCCESS")
					body = json.loads(result["body"].decode("utf-8"))
					upload = GameUpload.objects.get(id = body["id"])
					self.assertIsNotNone(upload)

	def test_all_integrations(self):
		for descriptor, raw_log, test_uuid in self.get_raw_log_integration_fixtures():
			if descriptor["skip"].lower() == "false":
				# Finish preparing the event object...
				event = descriptor["event"]
				event["body"] = b64encode(raw_log.encode("utf-8"))
				event["x-hsreplay-api-key"] = str(self.agent.api_key)
				event["x-hsreplay-upload-token"] = str(self.token)
				context = descriptor["context"]

				# Invoke main handler code
				result = raw_log_upload_handler(event, context)

				# Begin verification process...
				if descriptor["expected_response_is_replay_id"].lower() == "true":
					# This test case expects a success, so now verify the correctness
					# of the replay records generated
					replay = GameReplayUpload.objects.get(id=result["replay_uuid"])
					self.assertIsNotNone(replay)
				else:
					# This test expects a failure, so assert the error string is what is expected.
					self.assertEqual(result["msg"], descriptor["expected_response_string"])
