from hsreplaynet.test.base import TestDataConsumerMixin
from django.test import LiveServerTestCase, TestCase
import requests
from web import models
from django.core.urlresolvers import reverse
from unittest.mock import MagicMock
from datetime import datetime
from zlib import compress
from django.conf import settings
from io import BytesIO

class ReplayUploadTests(TestCase):

	def setUp(self):
		super().setUp()
		self.log_data = "Log_Data".encode("utf-8")
		s3_obj = {
			'ContentEncoding' : 'gzip',
			'Body' : BytesIO(compress(self.log_data))
		}

		self.mock_s3_client = MagicMock()
		self.mock_s3_client.put_object = MagicMock()
		self.mock_s3_client.get_object = MagicMock(return_value = s3_obj)
		self.mock_s3_client.delete_object = MagicMock()

		models.get_s3_client = MagicMock(return_value = self.mock_s3_client)

		self.upload_agent = models.UploadAgentAPIKey.objects.create(
			full_name = "Test Upload Agent",
			email = "test@agent.com",
			website = "http://testagent.com"
		)
		self.token = models.SingleSiteUploadToken.objects.create(requested_by_upload_agent = self.upload_agent)

	def test_save_read_delete(self):
		upload_date = datetime.now()

		upload = models.SingleGameRawLogUpload(upload_timestamp = upload_date,
											   match_start_timestamp = upload_date,
											   upload_token = self.token)
		upload.log = self.log_data
		upload.save()

		expected_key = upload_date.strftime('%Y/%m/%d/') + str(upload.id)
		self.mock_s3_client.put_object.assert_called_with(Body=compress(self.log_data),
														  Bucket=settings.S3_RAW_LOG_STORAGE_BUCKET,
														  Key=expected_key,
														  ContentEncoding='gzip')

		self.assertEqual(expected_key, upload.storage_key)
		self.assertEqual(self.log_data, upload.log)

		# Now we retrieve an instance to confirm that we can retrieve the data from S3
		db_record = models.SingleGameRawLogUpload.objects.get(id = upload.id)
		self.assertEqual(db_record.log, self.log_data)
		self.mock_s3_client.get_object.assert_called_with(Bucket=settings.S3_RAW_LOG_STORAGE_BUCKET, Key=expected_key)

		db_record.delete()
		self.mock_s3_client.delete_object.assert_called_with(Bucket=settings.S3_RAW_LOG_STORAGE_BUCKET, Key=expected_key)

	def test_cannot_save_without_setting_log_field(self):

		upload_date = datetime.now()
		upload = models.SingleGameRawLogUpload(	upload_timestamp = upload_date,
										   		match_start_timestamp = upload_date,
										   		upload_token = self.token)
		self.assertIsNone(upload.log)

		with self.assertRaises(ValueError):
			upload.save()


