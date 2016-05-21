from base64 import b64encode
from hsreplaynet.test.base import TestDataConsumerMixin, CardDataBaseTest
from hsreplaynet.web.models import (
	UploadAgentAPIKey, SingleSiteUploadToken, GameReplayUpload
)
from ..uploads import raw_log_upload_handler


class TestRawLogUploadHandler(CardDataBaseTest, TestDataConsumerMixin):
	def setUp(self):
		super(TestRawLogUploadHandler, self).setUp()
		self.upload_agent = UploadAgentAPIKey.objects.create(
			full_name="Test Upload Agent",
			email="test@testagent.example.org",
			website="http://testagent.example.org"
		)
		self.token = SingleSiteUploadToken.objects.create(upload_agent=self.upload_agent)

	def test_all_integrations(self):
		for descriptor, raw_log, test_uuid in self.get_raw_log_integration_fixtures():
			if descriptor["skip"].lower() == "false":
				# Finish preparing the event object...
				event = descriptor["event"]
				event["body"] = b64encode(raw_log.encode("utf-8"))
				event["x-hsreplay-api-key"] = str(self.upload_agent.api_key)
				event["x-hsreplay-upload-token"] = str(self.token.token)
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
