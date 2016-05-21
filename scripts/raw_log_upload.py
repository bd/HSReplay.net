"""
This command line tool is intended to simulate HDT uploading
a raw log to the web server.
"""
import json
import sys
import requests

upload_tokens = [
	"0adf879704bf46c1adbfaecf954079c2",
	"e422a2b3b8e04e078e26d129dc4c20c8",
	"cef9a4d279dd478abc230773201da0b2",
	"363b0be8e892456580ede3ca2189de85",
	"fb938a3b47814d54b348b1b06085f6c0",
]

API_KEY = "d1050cd9e8ed4ff7853dd109ee428505"
UPLOAD_TOKEN = upload_tokens[4]
HOST = "https://upload.hsreplay.net/api/v1/replay/upload/raw"
QUERY_PARAMS = {
	# "player_1_rank" : 18
	# "match_start_timestamp" : "2016-05-10T17:10:06.4923855+02:00"
}
HEADERS = {
	"x-hsreplay-api-key": API_KEY,
	"x-hsreplay-upload-token": UPLOAD_TOKEN,
}


def main(path):
	with open(path, "r") as f:
		data = f.read()

	response = requests.post(HOST, data=data, params=QUERY_PARAMS, headers=HEADERS)
	print(response.status_code)
	print(response.content)
	print(response.content.decode("utf-8"))
	result = json.loads(response.content.decode("utf-8"))
	print(result)


if __name__ == "__main__":
	main(sys.argv[1])
