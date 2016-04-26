import boto3
from config.settings import S3_RAW_LOG_STORAGE_BUCKET
from zlib import compress, decompress


class RawLogUploadHandler:

	def __init__(self, s3=None):
		self._s3 = s3 if s3 else boto3.resource('s3')

	def process_raw_replay_log(self, log, match_start):
		s3_log_obj = self._s3.Object(S3_RAW_LOG_STORAGE_BUCKET, "foo")
		s3_log_obj.put(Body=compress(log), ContentEncoding='gzip')
