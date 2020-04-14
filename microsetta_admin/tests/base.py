import unittest
from microsetta_admin.server import app


class TestBase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
