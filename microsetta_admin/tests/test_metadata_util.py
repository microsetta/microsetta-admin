import unittest
from microsetta_admin.metadata_util import (_build_col_name,
                                            _build_values_per_question,
                                            _find_duplicates,
                                            _fetch_barcode_metadata,
                                            retrieve_metadata)


class MetadataUtilTests(unittest.TestCase):
    def test_build_col_name(self):
        tests_and_expected = [('foo', 'bar', 'foo_bar'),
                              ('foo', 'bar baz', 'foo_bar_baz'),
                              ('foo', "bar'/%baz", 'foo_barbaz')]
        for col_name, value, exp in tests_and_expected:
            obs = _build_col_name(col_name, value)
            self.assertEqual(obs, exp)

    def test_build_values_per_question(self):
        pass

    def test_find_duplicates(self):
        exp = {'foo', 'bar'}
        obs = _find_duplicates(['foo', 'bar', 'foo', 'bar', 'baz'])
        self.assertEqual(obs, exp)

        exp = set()
        obs = _find_duplicates(['foo', 'bar'])
        self.assertEqual(obs, exp)

    def test_fetch_barcode_metadata(self):
        pass

    def test_retrieve_metadata(self):
        self.fail()


if __name__ == '__main__':
    unittest.main()
