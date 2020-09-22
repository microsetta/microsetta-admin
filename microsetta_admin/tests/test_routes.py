import json
from copy import deepcopy

from microsetta_admin.tests.base import TestBase


class DummyResponse(object):
    def __init__(self, status_code, output_dict):
        self.status_code = status_code
        self.text = json.dumps(output_dict)
        self.json = lambda: output_dict


class RouteTests(TestBase):
    PROJ_LIST = [{'additional_contact_name': None,
                  'alias': None,
                  'bank_samples': False,
                  'branding_associated_instructions': None,
                  'branding_status': None,
                  'collection': None,
                  'computed_stats': {
                      'num_fully_returned_kits': 1,
                      'num_kits': 5,
                      'num_kits_w_problems': 0,
                      'num_no_associated_source': 0,
                      'num_no_collection_info': 0,
                      'num_no_registered_account': 0,
                      'num_partially_returned_kits': 1,
                      'num_received_unknown_validity': 0,
                      'num_sample_is_valid': 4,
                      'num_samples': 20,
                      'num_samples_received': 4,
                      'num_unique_sources': 4},
                  'contact_email': None,
                  'contact_name': None,
                  'coordination': None,
                  'deadlines': None,
                  'disposition_comments': None,
                  'do_16s': None,
                  'do_mass_spec': None,
                  'do_metatranscriptomics': None,
                  'do_other': None,
                  'do_rt_qpcr': None,
                  'do_serology': None,
                  'do_shallow_shotgun': None,
                  'do_shotgun': None,
                  'is_blood': None,
                  'is_fecal': None,
                  'is_microsetta': False,
                  'is_other': None,
                  'is_saliva': None,
                  'is_skin': None,
                  'mass_spec_comments': None,
                  'mass_spec_contact_email': None,
                  'mass_spec_contact_name': None,
                  'num_subjects': None,
                  'num_timepoints': None,
                  'plating_start_date': None,
                  'project_id': 8,
                  'project_name': 'Project - %u[zGmÅq=g',
                  'sponsor': None,
                  'start_date': None,
                  'subproject_name': None},
                 {'additional_contact_name': None,
                  'alias': None,
                  'bank_samples': False,
                  'branding_associated_instructions': None,
                  'branding_status': None,
                  'collection': None,
                  'computed_stats': {
                      'num_fully_returned_kits': 4,
                      'num_kits': 5,
                      'num_kits_w_problems': 1,
                      'num_no_associated_source': 1,
                      'num_no_collection_info': 0,
                      'num_no_registered_account': 0,
                      'num_partially_returned_kits': 1,
                      'num_received_unknown_validity': 0,
                      'num_sample_is_valid': 2,
                      'num_samples': 12,
                      'num_samples_received': 5,
                      'num_unique_sources': 2},
                  'contact_email': None,
                  'contact_name': None,
                  'coordination': None,
                  'deadlines': None,
                  'disposition_comments': None,
                  'do_16s': None,
                  'do_mass_spec': None,
                  'do_metatranscriptomics': None,
                  'do_other': None,
                  'do_rt_qpcr': None,
                  'do_serology': None,
                  'do_shallow_shotgun': None,
                  'do_shotgun': None,
                  'is_blood': None,
                  'is_fecal': None,
                  'is_microsetta': False,
                  'is_other': None,
                  'is_saliva': None,
                  'is_skin': None,
                  'mass_spec_comments': None,
                  'mass_spec_contact_email': None,
                  'mass_spec_contact_name': None,
                  'num_subjects': None,
                  'num_timepoints': None,
                  'plating_start_date': None,
                  'project_id': 12,
                  'project_name': 'New proj',
                  'sponsor': None,
                  'start_date': None,
                  'subproject_name': "sub sub"}
                 ]

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

        response = self.app.post('/search/sample',
                                 data={'search_samples': '000004216'},
                                 follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<h3>Microsetta Search</h3>', response.data)

    def test_search_missing_barcode(self):
        # server side issues a GET to the API
        self.mock_get.return_value = DummyResponse(404, {})

        response = self.app.post('/search/sample',
                                 data={'search_samples': 'missing'},
                                 follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Query not found', response.data)

    def test_scan_simple(self):
        response = self.app.get('/scan', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<h3>Microsetta Scan</h3>', response.data)

    def test_scan_specific_no_warnings(self):
        resp1 = {
            "barcode_info": {"barcode": "000004216"},
            "projects_info": [],
            "scans_info": [],
            "latest_scan": None,
            "sample": {'site': 'baz'},
            "source": {'name': 'a source a name',
                       'source_type': 'human',
                       'source_data': {'description': None}},
            "account": {'id': 'd8592c74-9694-2135-e040-8a80115d6401'}
        }

        api_get_1 = DummyResponse(200, resp1)
        api_get_2 = DummyResponse(200, [])
        self.mock_get.side_effect = [api_get_1, api_get_2]

        response = self.app.get('/scan?sample_barcode=000004216',
                                follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<td>000004216</td>', response.data)
        self.assertNotIn(b'Status Warnings:', response.data)

    def test_scan_specific_no_collection_info_warning(self):
        resp1 = {
            "barcode_info": {"barcode": "000004216"},
            "projects_info": [{
                "project": "American Gut Project",
                "is_microsetta": True,
                "bank_samples": False,
                "plating_start_date": None
            }],
            "scans_info": [],
            "latest_scan": None,
            "sample": {'datetime_collected': None},
            "account": {'id': "ThizIzNotReal"},
            "source": {'name': 'a source a name',
                       'source_type': 'human',
                       'source_data': {'description': None}},
        }

        api_get_1 = DummyResponse(200, resp1)
        api_get_2 = DummyResponse(200, [])
        self.mock_get.side_effect = [api_get_1, api_get_2]

        response = self.app.get('/scan?sample_barcode=000004216',
                                follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<td>000004216</td>', response.data)
        self.assertIn(b'Status Warning: no-collection-info', response.data)

    def test_scan_specific_no_associated_source_warning(self):
        resp1 = {"barcode_info": {"barcode": "000004216"},
                 "projects_info": [{
                     "project": "American Gut Project",
                     "is_microsetta": True,
                     "bank_samples": False,
                     "plating_start_date": None
                 }],
                 "scans_info": [],
                 "latest_scan": None,
                 "sample": None,
                 "account": {"id": "foo"},
                 "source": None}

        api_get_1 = DummyResponse(200, resp1)
        api_get_2 = DummyResponse(200, [])
        self.mock_get.side_effect = [api_get_1, api_get_2]

        response = self.app.get('/scan?sample_barcode=000004216',
                                follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<td>000004216</td>', response.data)
        self.assertIn(b'Status Warning: no-associated-source', response.data)

    def test_scan_specific_no_registered_account_warning(self):
        resp = {"barcode_info": {"barcode": "000004216"},
                "projects_info": [{
                    "project": "American Gut Project",
                    "is_microsetta": True,
                    "bank_samples": False,
                    "plating_start_date": None
                }],
                "scans_info": [],
                "latest_scan": None,
                "sample": None,
                "account": None,
                "source": None}
        self.mock_get.return_value = DummyResponse(200, resp)

        response = self.app.get('/scan?sample_barcode=000004216',
                                follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<td>000004216</td>', response.data)
        self.assertIn(b'Status Warning: no-registered-account', response.data)

    def test_scan_specific_received_unknown_validity_warning(self):
        resp = {"barcode_info": {"barcode": "000004216"},
                "projects_info": [],
                "scans_info": [],
                "latest_scan": None,
                "sample": None,
                "account": None,
                "source": None}
        self.mock_get.return_value = DummyResponse(200, resp)

        response = self.app.get('/scan?sample_barcode=000004216',
                                follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<td>000004216</td>', response.data)
        self.assertIn(b'Status Warning: received-unknown-validity',
                      response.data)

    def test_create_kits_simple(self):
        self.mock_get.return_value = DummyResponse(200,
                                                   [{"project_name": "foo"}])

        response = self.app.get('/create_kits', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<h3>Microsetta Create Kits</h3>', response.data)

    def test_create_project_success(self):
        api_post_dummy = DummyResponse(201, {})
        api_get_dummy = DummyResponse(200, self.PROJ_LIST)
        self.mock_post.return_value = api_post_dummy
        self.mock_get.return_value = api_get_dummy

        create_input = deepcopy(self.PROJ_LIST[1])
        create_input["project_id"] = ""
        create_input.pop('computed_stats')
        response = self.app.post('/manage_projects',
                                 data=create_input,
                                 follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # if the below is on the page, the table of projects is shown
        self.assertIn(b'<th>Flight Sub-Project Name</th>', response.data)

    def test_create_project_fail(self):
        self.mock_post.return_value = DummyResponse(401, {})

        create_input = deepcopy(self.PROJ_LIST[1])
        create_input["project_id"] = ""
        create_input.pop('computed_stats')
        response = self.app.post('/manage_projects',
                                 data=create_input,
                                 follow_redirects=True)
        # the api call failed, but the admin page call succeeds--in returning
        # a page reporting the error :)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Unable to create project.', response.data)

    def test_update_project_success(self):
        self.mock_put.return_value = DummyResponse(204, {})
        self.mock_get.return_value = DummyResponse(200, self.PROJ_LIST)

        create_input = deepcopy(self.PROJ_LIST[1])
        create_input.pop('computed_stats')
        response = self.app.post('/manage_projects',
                                 data=create_input,
                                 follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # if the below is on the page, the table of projects is shown
        self.assertIn(b'<th>Flight Sub-Project Name</th>', response.data)

    def test_update_project_fail(self):
        self.mock_put.return_value = DummyResponse(400, {})

        create_input = deepcopy(self.PROJ_LIST[1])
        create_input.pop('computed_stats')
        response = self.app.post('/manage_projects',
                                 data=create_input,
                                 follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # the api call failed, but the admin page call succeeds--in returning
        # a page reporting the error :)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Unable to update project.', response.data)

    def test_manage_projects_success(self):
        self.mock_get.return_value = DummyResponse(200, self.PROJ_LIST)

        response = self.app.get('/manage_projects', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # if the below is on the page, the table of projects is shown
        self.assertIn(b'<th>Flight Sub-Project Name</th>', response.data)

    def test_manage_projects_fail(self):
        self.mock_get.return_value = DummyResponse(
            400, {"message": "hideous error"})

        response = self.app.get('/manage_projects', follow_redirects=True)
        # the api call failed, but the admin page call succeeds--in returning
        # a page reporting the error :)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Unable to load project list.', response.data)
