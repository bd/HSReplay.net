#from django.test import TestCase
from unittest import TestCase
from lambdas.uploads import RawLogUploadHandler
from unittest.mock import MagicMock
from config.settings import S3_RAW_LOG_STORAGE_BUCKET
from zlib import compress
from datetime import datetime

class TestRawLogUploadHandler(TestCase):

	def setUp(self):
		self._s3_mock = MagicMock()
		self._mock_object = MagicMock()
		self._mock_object.put = MagicMock()
		self._s3_mock.Object = MagicMock(return_value=self._mock_object)

		self._handler = RawLogUploadHandler(self._s3_mock)
		self._log_as_bytes = "Line1\nLine2\n".encode("utf8")
		self._match_start = datetime.now()

	def test_handler_required_arguments(self):
		# with self.assertRaises(TypeError) as context:
		# 	self._handler.process_raw_replay_log(self._log_as_bytes)
		pass

	def test_logs_written_to_s3(self):

		self._handler.process_raw_replay_log(self._log_as_bytes, self._match_start)
		self._expected_key = "foo"

		self._s3_mock.Object.assert_called_with(S3_RAW_LOG_STORAGE_BUCKET, self._expected_key)
		self._mock_object.put.assert_called_with(Body=compress(self._log_as_bytes), ContentEncoding='gzip')

	def test_raw_logs_expected_metadata(self):
		pass
