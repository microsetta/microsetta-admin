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
        response = self.app.post('/search',
                                 data={'search_term': '000004216'},
                                 follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<h3>Microsetta Search Result</h3>', response.data)
        self.assertIn(b'd8592c74-9699-2135-e040-8a80115d6401', response.data)

    def test_search_missing_barcode(self):
        response = self.app.post('/search',
                                 data={'search_term': 'missing'},
                                 follow_redirects=True)
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'<h3>Microsetta Search Result</h3>', response.data)

    def test_scan_simple(self):
        response = self.app.get('/scan', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<h3>Microsetta Scan</h3>', response.data)

    def test_create_simple(self):
        response = self.app.get('/create', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<h3>Microsetta Create</h3>', response.data)
