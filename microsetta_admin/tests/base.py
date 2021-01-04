from unittest import TestCase
from unittest.mock import patch
import pkg_resources
from microsetta_admin.server import app


class TestBase(TestCase):
    package = "microsetta_admin.tests"

    def setUp(self):
        # mocking derived from
        # https://realpython.com/testing-third-party-apis-with-mocks/
        self.mock_get_patcher = patch('microsetta_admin._api.requests.get')
        self.mock_get = self.mock_get_patcher.start()
        self.mock_put_patcher = patch('microsetta_admin._api.requests.put')
        self.mock_put = self.mock_put_patcher.start()
        self.mock_post_patcher = patch('microsetta_admin._api.requests.post')
        self.mock_post = self.mock_post_patcher.start()

        app.testing = True
        self.app = app.test_client()

        self.mock_session_patcher = patch("microsetta_admin._api.session",
                                          dict(token='42'))
        self.mock_session = self.mock_session_patcher.start()

    def tearDown(self):
        self.mock_get_patcher.stop()
        self.mock_put_patcher.stop()
        self.mock_post_patcher.stop()
        self.mock_session_patcher.stop()

    def get_data_path(self, filename):
        # adapted from qiime2.plugin.testing.TestPluginBase
        return pkg_resources.resource_filename(self.package,
                                               'data/%s' % filename)
