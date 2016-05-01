from django.test import TestCase
from web import models
from django.utils.timezone import now
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from unittest.mock import patch


class ReplayUploadTests(TestCase):

	def setUp(self):
		super().setUp()
		self.log_data = "Log_Data".encode("utf-8")

		self.upload_agent = models.UploadAgentAPIKey.objects.create(
			full_name = "Test Upload Agent",
			email = "test@agent.com",
			website = "http://testagent.com"
		)
		self.token = models.SingleSiteUploadToken.objects.create(requested_by_upload_agent = self.upload_agent)

	# We patch S3Storage because we don't want to be interacting with S3 in unit tests
	# You can temporarily comment out the @patch line to run the test in "integration mode" against S3. It should pass.
	@patch('storages.backends.s3boto.S3BotoStorage', FileSystemStorage)
	def test_save_read_delete(self):
		upload_date = now()

		upload = models.SingleGameRawLogUpload(upload_timestamp = upload_date,
											   match_start_timestamp = upload_date,
											   upload_token = self.token)

		upload.log.save('Power.log', ContentFile(self.log_data))
		upload.save()

		# Now we retrieve an instance to confirm that we can retrieve the data from S3
		db_record = models.SingleGameRawLogUpload.objects.get(id = upload.id)
		self.assertEqual(db_record.log.read(), self.log_data)

		db_record.delete()


