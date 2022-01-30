import unittest
import endpoint
import json
from functions import file_handler

class BotTestSuite(unittest.TestCase):

    def test_exists(self):
        self.assertTrue(
            all([endpoint.moodle_session, endpoint.bnes_moodle_session]),
            "Found required cookies")

    def test_page_reached(self):
        self.assertEqual(endpoint.r.url, endpoint.SECURE_URL)

    def test_notifications_exist(self):
        resp = json.loads(file_handler("results.json"))
        self.assertTrue(type(resp) != dict, "JSON response returned an error")


if __name__ == '__main__':
    unittest.main()
