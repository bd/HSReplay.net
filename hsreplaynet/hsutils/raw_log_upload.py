""" This command line tool is intended to simulate HDT uploading a raw log to the web server."""
import requests

upload_tokens = ['0adf879704bf46c1adbfaecf954079c2',
				 'e422a2b3b8e04e078e26d129dc4c20c8',
				 'cef9a4d279dd478abc230773201da0b2',
				 '363b0be8e892456580ede3ca2189de85',
				 'fb938a3b47814d54b348b1b06085f6c0',]

API_KEY = 'd1050cd9e8ed4ff7853dd109ee428505'
UPLOAD_TOKEN = upload_tokens[3]
HOST = 'https://upload.hsreplay.net/api/v1/replay/upload/raw'
#RAW_LOG_PATH = '/Users/awilson/PycharmProjects/hsreplaynet/hsreplaynet/test/integration_data/empty_raw_log_file_test/test_Data.log'
RAW_LOG_PATH = '/Users/awilson/Downloads/76d57f67-9ebb-4fc2-8b06-0cfd9cd564be.log'
QUERY_PARAMS = {
	# 'player_1_rank' : 18
	# 'match_start_timestamp' : '2016-05-10T17:10:06.4923855+02:00'
}
HEADERS = {
	'x-hsreplay-api-key':API_KEY,
	'x-hsreplay-upload-token':UPLOAD_TOKEN
}

data = open(RAW_LOG_PATH).read()
response = requests.post(HOST, data=data, params=QUERY_PARAMS, headers=HEADERS)
print(response.status_code)
print(response.content)
