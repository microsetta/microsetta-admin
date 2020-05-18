import unittest
import json
import pandas as pd
import pandas.testing as pdt
from microsetta_admin.tests.base import TestBase
from microsetta_admin.metadata_util import (_build_col_name,
                                            _find_duplicates,
                                            _fetch_barcode_metadata,
                                            _to_pandas_series,
                                            _to_pandas_dataframe,
                                            retrieve_metadata)


class MetadataUtilTests(TestBase):
    def setUp(self):
        self.raw_sample_1 = {
                'sample_barcode': '000004216',
                'host_subject_id': 'foo',
                'account': 'ignored',
                'source': 'ignored',
                'sample': 'ignored',
                'survey_answers': [
                    {'template': 1,
                     'response': {'1': ['DIET_TYPE', 'Omnivore'],
                                  '2': ['MULTIVITAMIN', 'No'],
                                  '3': ['PROBIOTIC_FREQUENCY', 'Unspecified'],
                                  '4': ['VITAMIN_B_SUPPLEMENT_FREQUENCY',
                                        'Unspecified'],
                                  '5': ['VITAMIN_D_SUPPLEMENT_FREQUENCY',
                                        'Unspecified'],
                                  '6': ['OTHER_SUPPLEMENT_FREQUENCY', 'No'],
                                  '9': ['ALLERGIC_TO', ['blahblah',
                                                        'stuff']]}},
                    {'template': 'blah',
                     'response': {'1': ['abc', 'okay'],
                                  '2': ['def', 'No']}}]}

        self.raw_sample_2 = {
                'sample_barcode': 'XY0004216',
                'host_subject_id': 'bar',
                'account': 'ignored',
                'source': 'ignored',
                'sample': 'ignored',
                'survey_answers': [
                    {'template': 1,
                     'response': {'1': ['DIET_TYPE', 'Vegan'],
                                  '2': ['MULTIVITAMIN', 'Yes'],
                                  '3': ['PROBIOTIC_FREQUENCY', 'Unspecified'],
                                  '4': ['VITAMIN_B_SUPPLEMENT_FREQUENCY',
                                        'Unspecified'],
                                  '5': ['VITAMIN_D_SUPPLEMENT_FREQUENCY',
                                        'Unspecified'],
                                  '6': ['OTHER_SUPPLEMENT_FREQUENCY', 'No'],
                                  '123': ['SAMPLE2SPECIFIC', 'foobar'],
                                  '9': ['ALLERGIC_TO', ['baz',
                                                        'stuff']]}}]}
        super().setUp()

    def test_build_col_name(self):
        tests_and_expected = [('foo', 'bar', 'foo_bar'),
                              ('foo', 'bar baz', 'foo_bar_baz'),
                              ('foo', "bar'/%baz", 'foo_barbaz')]
        for col_name, value, exp in tests_and_expected:
            obs = _build_col_name(col_name, value)
            self.assertEqual(obs, exp)

    def test_find_duplicates(self):
        exp = {'foo', 'bar'}
        exp_errors = {'barcode': ['foo', 'bar'],
                      'error': "Duplicated barcodes in input"}
        obs, errors = _find_duplicates(['foo', 'bar', 'foo', 'bar', 'baz'])
        self.assertEqual(obs, exp)
        self.assertEqual(sorted(errors['barcode']),
                         sorted(exp_errors['barcode']))

        exp = set()
        obs, errors = _find_duplicates(['foo', 'bar'])
        self.assertEqual(obs, exp)
        self.assertEqual(errors, None)

    def test_fetch_barcode_metadata(self):
        res = {'sample_barcode': '000004216'}
        self.mock_get.return_value.status_code = 200
        self.mock_get.return_value.json = lambda: res
        self.mock_get.return_value.text = json.dumps(res)

        obs, obs_errors = _fetch_barcode_metadata('000004216')

        # verify we obtained metadata. it is not the responsibility of this
        # test to assert the structure of the metadata as that is the scope of
        # the admin interfaces on the private API
        self.assertEqual(obs['sample_barcode'], '000004216')
        self.assertEqual(obs_errors, None)

    def test_fetch_barcode_metadata_missing(self):
        res = {}
        self.mock_get.return_value.status_code = 404
        self.mock_get.return_value.json = lambda: res
        self.mock_get.return_value.text = json.dumps(res)

        obs, obs_errors = _fetch_barcode_metadata('badbarcode')
        self.assertNotIn('sample_barcode', obs)
        self.assertEqual(obs_errors, {'barcode': 'badbarcode',
                                      'error': "404 from api"})

    def test_to_pandas_dataframe(self):
        data = [self.raw_sample_1, self.raw_sample_2]
        exp = pd.DataFrame([['000004216', 'foo', 'Omnivore', 'No',
                             'Unspecified', 'Unspecified', 'Unspecified', 'No',
                             'true', 'true', 'false', 'Missing: not provided',
                             'okay', 'No'],
                            ['XY0004216', 'bar', 'Vegan', 'Yes', 'Unspecified',
                             'Unspecified', 'Unspecified', 'No',
                             'false', 'true', 'true', 'foobar',
                             'Missing: not provided',
                             'Missing: not provided']],
                           columns=['sample_name', 'HOST_SUBJECT_ID',
                                    'DIET_TYPE', 'MULTIVITAMIN',
                                    'PROBIOTIC_FREQUENCY',
                                    'VITAMIN_B_SUPPLEMENT_FREQUENCY',
                                    'VITAMIN_D_SUPPLEMENT_FREQUENCY',
                                    'OTHER_SUPPLEMENT_FREQUENCY',
                                    'ALLERGIC_TO_blahblah',
                                    'ALLERGIC_TO_stuff', 'ALLERGIC_TO_baz',
                                    'SAMPLE2SPECIFIC', 'abc', 'def']
                           ).set_index('sample_name')
        obs = _to_pandas_dataframe(data)
        pdt.assert_frame_equal(obs, exp, check_like=True)

    def test_to_pandas_series(self):
        data = self.raw_sample_1

        exp = pd.Series(['foo', 'Omnivore', 'No', 'Unspecified', 'Unspecified',
                         'Unspecified', 'No', 'true', 'true', 'okay', 'No'],
                        index=['HOST_SUBJECT_ID', 'DIET_TYPE', 'MULTIVITAMIN',
                               'PROBIOTIC_FREQUENCY',
                               'VITAMIN_B_SUPPLEMENT_FREQUENCY',
                               'VITAMIN_D_SUPPLEMENT_FREQUENCY',
                               'OTHER_SUPPLEMENT_FREQUENCY',
                               'ALLERGIC_TO_blahblah',
                               'ALLERGIC_TO_stuff', 'abc', 'def'],
                        name='000004216')
        exp_multi = set(['ALLERGIC_TO_blahblah', 'ALLERGIC_TO_stuff'])
        obs, obs_multi = _to_pandas_series(data)
        pdt.assert_series_equal(obs, exp)
        self.assertEqual(obs_multi, exp_multi)


if __name__ == '__main__':
    unittest.main()
