import json

from microsetta_admin.tests.base import TestBase


class RouteTests(TestBase):
    def test_home_simple(self):
        response = self.app.get('/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<title>Microsetta Admin</title>', response.data)

    def test_search_simple(self):
        response = self.app.get('/search', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<h3>Microsetta Search</h3>', response.data)

    def test_search_specific_barcode(self):
        # server side issues a GET to the API
        self.mock_get.return_value.status_code = 200

        response = self.app.post('/search',
                                 data={'search_term': '000004216'},
                                 follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<h3>Microsetta Search Result</h3>', response.data)

    def test_search_missing_barcode(self):
        # server side issues a GET to the API
        self.mock_get.return_value.status_code = 200
        self.mock_get.return_value.text = '{"kit": None}'
        self.mock_get.return_value.json = lambda: {"kit": None}  # noqa

        response = self.app.post('/search',
                                 data={'search_term': 'missing'},
                                 follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'missing not found', response.data)

    def test_scan_simple(self):
        response = self.app.get('/scan', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<h3>Microsetta Scan</h3>', response.data)

    def test_scan_specific_okay(self):
        resp = {"barcode_info": {"barcode": "000004216"},
                "sample": {'site': 'baz'},
                "account": 'foo',
                "source": 'bar'}

        self.mock_get.return_value.status_code = 200
        self.mock_get.return_value.text = json.dumps(resp)
        self.mock_get.return_value.json = lambda: resp  # noqa

        response = self.app.get('/scan?sample_barcode=000004216',
                                follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<td>000004216</td>', response.data)
        self.assertNotIn(b'Status Warnings:', response.data)

    def test_scan_specific_uncollected(self):
        resp = {"barcode_info": {"barcode": "000004216"},
                "sample": {'site': None},
                "account": 'foo',
                "source": 'bar'}

        self.mock_get.return_value.status_code = 200
        self.mock_get.return_value.text = json.dumps(resp)
        self.mock_get.return_value.json = lambda: resp  # noqa

        response = self.app.get('/scan?sample_barcode=000004216',
                                follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<td>000004216</td>', response.data)
        self.assertIn(b'Sample site not specified', response.data)

    def test_scan_specific_no_account(self):
        resp = {"barcode_info": {"barcode": "000004216"},
                "sample": None,
                "account": None,
                "source": 'bar'}

        self.mock_get.return_value.status_code = 200
        self.mock_get.return_value.text = json.dumps(resp)
        self.mock_get.return_value.json = lambda: resp  # noqa

        response = self.app.get('/scan?sample_barcode=000004216',
                                follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<td>000004216</td>', response.data)
        self.assertIn(b'No associated account', response.data)

    def test_scan_specific_no_source(self):
        resp = {"barcode_info": {"barcode": "000004216"},
                "sample": None,
                "account": None,
                "source": None}

        self.mock_get.return_value.status_code = 200
        self.mock_get.return_value.text = json.dumps(resp)
        self.mock_get.return_value.json = lambda: resp  # noqa

        response = self.app.get('/scan?sample_barcode=000004216',
                                follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<td>000004216</td>', response.data)
        self.assertIn(b'No associated source', response.data)

    def test_create_kits_simple(self):
        self.mock_get.return_value.status_code = 200
        self.mock_get.return_value.text = '[{"project_name": "foo"}]'
        self.mock_get.return_value.json = lambda: [{"project_name": "foo"}]

        response = self.app.get('/create_kits', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<h3>Microsetta Create Kits</h3>', response.data)

    def test_create_project_simple(self):
        response = self.app.get('/create_project', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<h3>Microsetta Create Project</h3>', response.data)
