from microsetta_admin.metadata_constants import MISSING_VALUE
from functools import reduce
from operator import or_
import pandas as pd
import numpy as np


class Transformer:
    REQUIRED_COLUMNS = None
    COLUMN_NAME = None
    UPDATE_EXISTING = None

    @classmethod
    def apply(cls, df):
        return cls._transform(df)

    @classmethod
    def _transform(cls, df):
        raise NotImplementedError

    @staticmethod
    def not_null_map(*args):
        return ~(reduce(or_, args))

    @classmethod
    def basis(cls, index):
        return pd.Series([None] * len(index), index=index,
                         name=cls.COLUMN_NAME)


class BMI(Transformer):
    REQUIRED_COLUMNS = frozenset(['weight_kg', 'height_cm'])
    COLUMN_NAME = 'bmi'

    @classmethod
    def _transform(cls, df):
        # weight in kilograms / (height in meters)^2
        weight = pd.to_numeric(df['weight_kg'], errors='coerce')
        height = pd.to_numeric(df['height_cm'], errors='coerce')
        height /= 100  # covert to meters
        height *= height  #

        not_null_map = cls.not_null_map(weight.isnull(),
                                        height.isnull())
        series = cls.basis(df.index)
        series.loc[not_null_map] = \
            (weight.loc[not_null_map] / height.loc[not_null_map]).round(1)
        return series.fillna(MISSING_VALUE)


class AgeYears(Transformer):
    REQUIRED_COLUMNS = frozenset(['birth_year', 'birth_month',
                                  'collection_timestamp'])
    COLUMN_NAME = 'age_years'

    @classmethod
    def _transform(cls, df):
        def make_month_year(row):
            mo = row['birth_month']
            yr = row['birth_year']
            if pd.isnull(mo) or pd.isnull(yr):
                return '-'
            else:
                return '%s-%s' % (mo, yr)

        birth_month_year = df.apply(make_month_year, axis=1)
        birth_month_year = pd.to_datetime(birth_month_year, errors='coerce',
                                          format='%B-%Y')
        collection_timestamp = pd.to_datetime(df['collection_timestamp'],
                                              errors='coerce')

        not_null_map = cls.not_null_map(birth_month_year.isnull(),
                                        collection_timestamp.isnull())

        series = cls.basis(df.index)

        collection_timestamp = collection_timestamp[not_null_map]
        birth_month_year = birth_month_year[not_null_map]

        # compute timedelta64 types, and express as year
        td = collection_timestamp - birth_month_year
        td_as_year = (td / np.timedelta64(1, 'Y')).round(1)
        series.loc[not_null_map] = td_as_year

        return series.fillna(MISSING_VALUE)


class AgeCat(Transformer):
    REQUIRED_COLUMNS = frozenset(['age_years', ])
    COLUMN_NAME = 'age_cat'

    @classmethod
    def _transform(cls, df):
        bounds = [('baby', 0, 3),
                  ('child', 3, 13),
                  ('teen', 13, 20),
                  ('20s', 20, 30),
                  ('30s', 30, 40),
                  ('40s', 40, 50),
                  ('50s', 50, 60),
                  ('60s', 60, 70),
                  ('70+', 70, 123)]

        age_years = pd.to_numeric(df['age_years'], errors='coerce')
        age_cat = cls.basis(df.index)

        for label, lower, upper in bounds:
            positions = (age_years >= lower) & (age_years < upper)
            age_cat.loc[positions] = label

        return age_cat.fillna(MISSING_VALUE)


class BMICat(Transformer):
    REQUIRED_COLUMNS = frozenset(['bmi', ])
    COLUMN_NAME = 'bmi_cat'

    @classmethod
    def _transform(cls, df):
        bounds = [('Underweight', 8, 18.5),
                  ('Normal', 18.5, 25),
                  ('Overweight', 25, 30),
                  ('Obese', 30, 80)]
        bmi = pd.to_numeric(df['bmi'], errors='coerce')
        bmi_cat = cls.basis(df.index)

        for label, lower, upper in bounds:
            positions = (bmi >= lower) & (bmi < upper)
            bmi_cat.loc[positions] = label

        return bmi_cat


class AlcoholConsumption(Transformer):
    REQUIRED_COLUMNS = frozenset(['alcohol_frequency', ])
    COLUMN_NAME = 'alcohol_consumption'

    @classmethod
    def _transform(cls, df):
        mapping = {'Rarely (a few times/month)': 'Yes',
                   'Occasionally (1-2 times/week)': 'Yes',
                   'Regularly (3-5 times/week)': 'Yes',
                   'Daily': 'Yes',
                   'Never': 'No'}
        series = df['alcohol_frequency'].replace(mapping, inplace=False)
        series.name = cls.COLUMN_NAME
        return series


def _normalizer(df, focus_col, units_col, units_value, factor):
    # get our columns
    focus = pd.to_numeric(df[focus_col], errors='coerce')
    units = df[units_col]

    # operate on a copy as to retain non-unit focus values (e.g., values
    # already expressed as centimeters
    result = focus.copy()

    # anything negative is weird so kill it
    result[result < 0] = None

    # figure out what positions are safe to operate on
    not_null_map = Transformer.not_null_map(result.isnull(),
                                            units.isnull())

    # take entries like where either focus or units are null and kill them
    result.loc[not_null_map[~not_null_map].index] = None

    # reduce to only those safe to operate on
    focus_not_null = result[not_null_map]
    units_not_null = units[not_null_map]
    focus_adj = focus_not_null.loc[units_not_null == units_value]

    # adjust the indices that need adjustment
    result.loc[focus_adj.index] = focus_adj * factor

    return result.fillna(MISSING_VALUE)


class _Normalize(Transformer):
    FOCUS_COL = None
    FOCUS_UNITS = None
    UNITS_COL = None
    FACTOR = None

    @classmethod
    def _transform(cls, df):
        return _normalizer(df, cls.FOCUS_COL, cls.UNITS_COL, cls.FOCUS_UNITS,
                           cls.FACTOR)


class NormalizeHeight(_Normalize):
    REQUIRED_COLUMNS = frozenset(['height_units', 'height_cm'])
    COLUMN_NAME = 'height_cm'
    UPDATE_EXISTING = ('height_units', 'centimeters')
    FOCUS_COL = 'height_cm'
    UNITS_COL = 'height_units'
    FOCUS_UNITS = 'inches'
    FACTOR = 2.54


class NormalizeWeight(_Normalize):
    REQUIRED_COLUMNS = frozenset(['weight_units', 'weight_cm'])
    COLUMN_NAME = 'weight_kg'
    UPDATE_EXISTING = ('weight_units', 'kilograms')
    FOCUS_COL = 'weight_kg'
    FOCUS_UNITS = 'pounds'
    UNITS_COL = 'weight_units'
    FACTOR = (1 / 2.20462)


# transforms are order dependent as some entries (e.g., BMICat) depend
# on the presence of a BMI column
HUMAN_TRANSFORMS = (AgeYears, AgeCat, NormalizeWeight, NormalizeHeight,
                    BMI, BMICat, AlcoholConsumption)


def apply_category_specific_transforms(df, transforms):
    for transform in transforms:
        # new columns are potentially added on each transform so recollect
        columns = set(df.columns)

        if transform.REQUIRED_COLUMNS.issubset(columns):
            # note: not using df.apply here as casts are needed on a
            # case-by-case basis, and pandas is much more efficient
            # casting whole columns
            subset = df[transform.REQUIRED_COLUMNS]
            series = transform.apply(subset)
            df[transform.COLUMN_NAME] = series.astype(str)

            # update a an existing column if the transform needs to
            if transform.UPDATE_EXISTING is not None:
                column, value = transform.UPDATE_EXISTING
                df.loc[~df[transform.COLUMN_NAME.isnull()], column] = value

    return df
