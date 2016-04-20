import boto3
import logging

logger = logging.getLogger(__name__)
s3 = boto3.resource('s3')


def fetch_s3_object(bucket, key):
	bucket = s3.Bucket(bucket)
	objs = list(bucket.objects.filter(Prefix=key))
	if len(objs) > 0 and objs[0].key == key:
		return objs[0].get()
	else:
		return None