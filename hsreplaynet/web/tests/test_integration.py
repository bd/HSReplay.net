from hsreplaynet.test.base import FunctionalTest, TestDataConsumerMixin
import requests


class ReplayUploadTests(FunctionalTest, TestDataConsumerMixin):

	def setUp(self):
		super().setUp()

	def test_replay_xml_upload(self):
		with open(self.replay_file_path('hslog.xml')) as xml_file:
			original_xml_data = xml_file.read()

			server_url = '%s%s' % (self.live_server_url, '/api/v1/replay/upload')
			response = requests.post(server_url, data=original_xml_data.encode("utf-8"))

			url_to_xml = response.headers['Location']
			print(url_to_xml)
			xml_back_from_server = requests.get(url_to_xml).content
			self.assertEqual(xml_back_from_server, original_xml_data.encode("utf-8"))
