import unittest
import json
import pandas as pd
import pandas.testing as pdt
from microsetta_admin.tests.base import TestBase
from microsetta_admin.metadata_constants import HUMAN_SITE_INVARIANTS
from microsetta_admin.metadata_util import (_build_col_name,
                                            _find_duplicates,
                                            _fetch_barcode_metadata,
                                            _to_pandas_series,
                                            _to_pandas_dataframe,
                                            _fetch_survey_template,
                                            _fetch_observed_survey_templates,
                                            _construct_multiselect_map,
                                            #_add_age_years,
                                            drop_private_columns)


class MetadataUtilTests(TestBase):
    def setUp(self):
        self.raw_sample_1 = {
                'sample_barcode': '000004216',
                'host_subject_id': 'foo',
                'source_type': 'human',
                'account': {'id': 'foo'},
                'source': {'id': 'bar'},
                "sample": {
                    "sample_projects": ["American Gut Project"],
                    "datetime_collected": "2013-10-15T09:30:00",
                    "site": "Stool"
                },
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
                    {'template': 10,
                     'response': {'1': ['abc', 'okay'],
                                  '2': ['def', 'No']}}]}

        self.raw_sample_2 = {
                'sample_barcode': 'XY0004216',
                'host_subject_id': 'bar',
                'source_type': 'human',
                'account': {'id': 'baz'},
                'source': {'id': 'bonkers'},
                "sample": {
                    "sample_projects": ["American Gut Project"],
                    "datetime_collected": "2013-10-15T09:30:00",
                    "site": "Stool"
                },
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

        self.fake_survey_template = {
            'survey_template_text': {
                'groups': [
                    {'fields': [
                        {'id': "5",
                         'shortname': 'foo',
                         'multi': False,
                         'values': ['a', 'b', 'c']},
                        {'id': "7",
                         'shortname': 'bar',
                         'multi': True,
                         'values': ['e', 'f', 'g  h']}
                        ]}]}}

        super().setUp()

    def test_construct_multiselect_map(self):
        templates = {1: self.fake_survey_template}
        exp = {(1, '7'): {'e': 'bar_e',
                          'f': 'bar_f',
                          'g  h': 'bar_g__h'}}
        obs = _construct_multiselect_map(templates)
        self.assertEqual(obs, exp)

    def test_fetch_observed_survey_templates(self):
        res = {'a': 'dict', 'of': 'stuff'}
        self.mock_get.return_value.status_code = 200
        self.mock_get.return_value.json = lambda: res
        self.mock_get.return_value.text = json.dumps(res)

        exp = {1: res, 10: res}
        obs, errors = _fetch_observed_survey_templates([self.raw_sample_1,
                                                        self.raw_sample_2])

        self.assertEqual(obs, exp)
        self.assertEqual(errors, None)

    def test_fetch_survey_template(self):
        res = {'a': 'dict', 'of': 'stuff'}
        self.mock_get.return_value.status_code = 200
        self.mock_get.return_value.json = lambda: res
        self.mock_get.return_value.text = json.dumps(res)

        survey, errors = _fetch_survey_template(1, {'account_id': 'foo',
                                                    'source_id': 'bar'})

        # verify we obtained data. it is not the responsibility of this
        # test to assert the structure of the metadata as that is the scope of
        # the admin interfaces on the private API
        self.assertEqual(survey, res)
        self.assertEqual(errors, None)

    def test_drop_private_columns(self):
        df = pd.DataFrame([[1, 2, 3], [4, 5, 6]],
                          columns=['pM_foo', 'okay', 'ABOUT_yourSELF_TEXT'])
        exp = pd.DataFrame([[2, ], [5, ]], columns=['okay'])
        obs = drop_private_columns(df)
        pdt.assert_frame_equal(obs, exp)

    def test_build_col_name(self):
        tests_and_expected = [('foo', 'bar', 'foo_bar'),
                              ('foo', 'bar baz', 'foo_bar_baz')]
        for col_name, value, exp in tests_and_expected:
            obs = _build_col_name(col_name, value)
            self.assertEqual(obs, exp)

        tests = [('foo', 'bar+'), ('foo', 'bar-')]
        for col_name, value in tests:
            with self.assertRaisesRegex(ValueError, "unsafe column name"):
                _build_col_name(col_name, value)

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
                             'okay', 'No', "2013-10-15T09:30:00"],
                            ['XY0004216', 'bar', 'Vegan', 'Yes', 'Unspecified',
                             'Unspecified', 'Unspecified', 'No',
                             'false', 'true', 'true', 'foobar',
                             'Missing: not provided',
                             'Missing: not provided',
                             "2013-10-15T09:30:00"]],
                           columns=['sample_name', 'HOST_SUBJECT_ID',
                                    'DIET_TYPE', 'MULTIVITAMIN',
                                    'PROBIOTIC_FREQUENCY',
                                    'VITAMIN_B_SUPPLEMENT_FREQUENCY',
                                    'VITAMIN_D_SUPPLEMENT_FREQUENCY',
                                    'OTHER_SUPPLEMENT_FREQUENCY',
                                    'ALLERGIC_TO_blahblah',
                                    'ALLERGIC_TO_stuff', 'ALLERGIC_TO_baz',
                                    'SAMPLE2SPECIFIC', 'abc', 'def',
                                    'COLLECTION_TIMESTAMP']
                           ).set_index('sample_name')

        for k, v in HUMAN_SITE_INVARIANTS['Stool'].items():
            exp[k] = v

        obs = _to_pandas_dataframe(data)
        pdt.assert_frame_equal(obs, exp, check_like=True)

    def test_to_pandas_series(self):
        data = self.raw_sample_1

        values = ['foo', 'Omnivore', 'No', 'Unspecified', 'Unspecified',
                  'Unspecified', 'No', 'true', 'true', 'okay', 'No',
                  "2013-10-15T09:30:00"]
        index = ['HOST_SUBJECT_ID', 'DIET_TYPE', 'MULTIVITAMIN',
                 'PROBIOTIC_FREQUENCY', 'VITAMIN_B_SUPPLEMENT_FREQUENCY',
                 'VITAMIN_D_SUPPLEMENT_FREQUENCY',
                 'OTHER_SUPPLEMENT_FREQUENCY',
                 'ALLERGIC_TO_blahblah', 'ALLERGIC_TO_stuff', 'abc', 'def',
                 'COLLECTION_TIMESTAMP']

        for k, v in HUMAN_SITE_INVARIANTS['Stool'].items():
            values.append(v)
            index.append(k)

        exp = pd.Series(values, index=index, name='000004216')
        exp_multi = set(['ALLERGIC_TO_blahblah', 'ALLERGIC_TO_stuff'])
        obs, obs_multi = _to_pandas_series(data)
        pdt.assert_series_equal(obs, exp.loc[obs.index])
        self.assertEqual(obs_multi, exp_multi)

    def test_age_years(self):
        df = pd.DataFrame([['1970', '10', 'human', "2013-10-15T09:30:00"],
                           ['1980', '11', 'animal',"2013-11-15T09:30:00"],
                           [None, '4', 'animal',"2013-11-15T09:30:00"],
                           # toss in some nonsense...
                           ['1990', '4', 'environmental',
                            "2013-11-15T09:30:00"]],
                          columns=['BIRTH_YEAR', 'BIRTH_MONTH', 'HOST_COMMON_NAME',
                              'COLLECTION_TIMESTAMP'])
        exp = df.copy()
        exp['AGE_YEARS'] = ['43.0', '33.0', None, None]
        _add_age_years(df)
        pdt.assert_frame_equal(df, exp)

    def test_bmi(self):
        pass

        # TODO: normalize height and weight before BMI calc
        #df = pd.DataFrame([['75', '170', 'human', 'kilograms', 'centimeters'],
        #                   ['150', '65', 'animal', 'pounds', 'inches'],
        #                   ['150', '65', 'human', 'pounds', 'inches'],
        #                   ['150', '65', 'human', None, 'inches'],
        #                   ['150', '65', 'human', 'pounds', None],
        #                   ['150', '170', 'human', 'pounds', 'centimeters'],
        #                   ['75', '65', 'human', 'kilograms', 'inches'],
        #                   [None, '4', 'human', 'pounds', 'inches'],
        #                   ['1990', '4', 'environmental']],
        #                  columns=['WEIGHT_KG', 'HEIGHT_CM',
        #                           'HOST_COMMON_NAME', 'WEIGHT_UNITS',
        #                           'HEIGHT_UNITS'])
        #exp = df.copy()
        #pdt.assert_frame_equal(df, exp)


if __name__ == '__main__':
    unittest.main()
