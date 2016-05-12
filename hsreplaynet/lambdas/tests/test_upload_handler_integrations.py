from base64 import b64encode
from django.core.files.storage import FileSystemStorage
from handlers import raw_log_upload_handler
from unittest.mock import patch
from test.base import TestDataConsumerMixin, CardDataBaseTest
from web.models import *


# We patch S3Storage because we don't want to be interacting with S3 in unit tests
# You can temporarily comment out the @patch line to run the test in "integration mode" against S3. It should pass.
@patch('storages.backends.s3boto.S3BotoStorage', FileSystemStorage)
class TestRawLogUploadHandler(CardDataBaseTest, TestDataConsumerMixin):
	def setUp(self):
		super().setUp()

		self.upload_agent = UploadAgentAPIKey.objects.create(
			full_name="Test Upload Agent",
			email="test@agent.com",
			website="http://testagent.com"
		)

		self.token = SingleSiteUploadToken.objects.create(requested_by_upload_agent=self.upload_agent)

	def test_all_integrations(self):

		for descriptor, raw_log, test_uuid in self.get_raw_log_integration_fixtures():
			if descriptor["skip"].lower() == 'false':

				# Finish preparing the event object...
				event = descriptor["event"]
				event['body'] = b64encode(raw_log.encode("utf-8"))
				event['x-hsreplay-api-key'] = str(self.upload_agent.api_key)
				event['x-hsreplay-upload-token'] = str(self.token.token)
				context = descriptor["context"]

				# Invoke main handler code
				result = raw_log_upload_handler(event, context)

				# Begin verification process...
				if descriptor["expected_response_is_replay_id"].lower() == 'true':
					# This test case expects a success, so now verify the correctness of the replay records generated
					replay = GameReplayUpload.objects.get(id=result)
					self.assertIsNotNone(replay)
					assertions = descriptor["expected_replay_assertions"]
				else:
					# This test expects a failure, so assert the error string is what is expected.
					self.assertEqual(result, descriptor["expected_response_string"])

