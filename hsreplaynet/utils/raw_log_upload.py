""" This command line tool is intended to simulate HDT uploading a raw log to the web server."""
import requests


API_KEY = 'd1050cd9e8ed4ff7853dd109ee428505'
UPLOAD_TOKEN = 'e422a2b3b8e04e078e26d129dc4c20c8'
HOST = 'https://upload.hsreplay.net/api/v1/replay/upload/raw'
RAW_LOG_PATH = '/Users/awilson/PycharmProjects/hsreplaynet/hsreplaynet/test/integration_data/empty_raw_log_file_test/test_Data.log'
QUERY_PARAMS = {
	# 'player_1_rank' : 18
	# 'match_start_timestamp' : '2016-05-10T17:10:06.4923855+02:00'
}
HEADERS = {
	'x-hsreplay-api-key':API_KEY,
	'x-hsreplay-upload-token':UPLOAD_TOKEN
}

url = HOST
data = open(RAW_LOG_PATH).read()
response = requests.post(url, data=data, params=QUERY_PARAMS, headers=HEADERS)
print(response.status_code)
print(response.content)
