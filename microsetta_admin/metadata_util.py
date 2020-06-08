from microsetta_admin._api import APIRequest
from microsetta_admin.metadata_constants import HUMAN_SITE_INVARIANTS
from collections import Counter
import re
import pandas as pd


EBI_REMOVE = ['ABOUT_YOURSELF_TEXT', 'ANTIBIOTIC_CONDITION',
              'ANTIBIOTIC_MED',
              'BIRTH_MONTH', 'CAT_CONTACT', 'CAT_LOCATION',
              'CONDITIONS_MEDICATION', 'DIET_RESTRICTIONS_LIST',
              'DOG_CONTACT',
              'DOG_LOCATION', 'GENDER', 'MEDICATION_LIST',
              'OTHER_CONDITIONS_LIST', 'PREGNANT_DUE_DATE',
              'RACE_OTHER',
              'RELATIONSHIPS_WITH_OTHERS_IN_STUDY',
              'SPECIAL_RESTRICTIONS',
              'SUPPLEMENTS', 'TRAVEL_LOCATIONS_LIST', 'ZIP_CODE',
              'WILLING_TO_BE_CONTACTED', 'pets_other_freetext']


#def _add_age_years(df):
#    """Add AGE_YEARS inplace to the dataframe"""
#    fields = {'BIRTH_YEAR': pd.to_numeric,
#              'BIRTH_MONTH': pd.to_numeric,
#              'HOST_COMMON_NAME': lambda x, errors: str(x),
#              'COLLECTION_TIMESTAMP': pd.to_datetime}
#
#    if set(fields).issubset(df.columns):
#        filtered = df[list(fields)].copy()
#        for c in filtered.columns:
#            filtered[c] = fields[c](df[col], errors='coerce')
#
#        births = []
#        for idx, row in filtered.iterrows():
#            dt = None
#            year = row['BIRTH_YEAR']
#            month = row['BIRTH_MONTH']
#            if not pd.isnull(year) \
#                    and not pd.isnull(month):
#                dt = datetime(year, month)
#
#        filtered['birth'] = [datetime(
#        birth_year = cast['BIRTH_YEAR']
#        birth_month = cast['BIRTH_MONTH']
#        hcn = cast['HOST_COMMON_NAME']
#        timestamp = cast['COLLECITON_TIMESTAMP']
#
#        birth_year_not_nulls = ~(birth_year.isnull())
#        birth_month_not_nulls = ~(birth_month.isnull())
#        hcn = hcn == 'human'
#        timestamp_not_nulls = ~(timestamp.isnull())
#
#        valid = np.logical_and.reduce([birth_year_not_nulls,
#                                       birth_month_not_nulls,
#                                       hcn, timestamp_not_nulls])
#
#        births = pd.Series(
#    else:
#        age_years = [None] * len(df)
#
#    df['AGE_YEARS'] = age_years


def add_bmi(df):
    foo = """
                  # convert numeric fields
                for field in ('HEIGHT_CM', 'WEIGHT_KG'):
                    md[1][barcode][field] = sub('[^0-9.]',
                                                '', md[1][barcode][field])
                    try:
                        md[1][barcode][field] = float(md[1][barcode][field])
                    except ValueError:
                        md[1][barcode][field] = 'Unspecified'

                # Correct height units
                if responses['HEIGHT_UNITS'] == 'inches' and \
                        isinstance(md[1][barcode]['HEIGHT_CM'], float):
                    md[1][barcode]['HEIGHT_CM'] = \
                        2.54 * md[1][barcode]['HEIGHT_CM']
                md[1][barcode]['HEIGHT_UNITS'] = 'centimeters'

                # Correct weight units
                if responses['WEIGHT_UNITS'] == 'pounds' and \
                        isinstance(md[1][barcode]['WEIGHT_KG'], float):
                    md[1][barcode]['WEIGHT_KG'] = \
                        md[1][barcode]['WEIGHT_KG'] / 2.20462
                md[1][barcode]['WEIGHT_UNITS'] = 'kilograms'

                if all([isinstance(md[1][barcode]['WEIGHT_KG'], float),
                        md[1][barcode]['WEIGHT_KG'] != 0.0,
                        isinstance(md[1][barcode]['HEIGHT_CM'], float),
                        md[1][barcode]['HEIGHT_CM'] != 0.0]):
                    md[1][barcode]['BMI'] = md[1][barcode]['WEIGHT_KG'] / \
                        (md[1][barcode]['HEIGHT_CM'] / 100)**2
                else:
                    md[1][barcode]['BMI'] = 'Unspecified'
    """



def drop_private_columns(df):
    """Remove columns that should not be shared publicly

    Parameters
    ----------
    df : pd.DataFrame
        The dataframe to operate on

    Returns
    -------
    pd.DataFrame
        The filtered dataframe
    """
    # The personal microbiome survey contains additional fields that are
    # sensitive in nature
    pm_remove = {c.lower() for c in df.columns if c.lower().startswith('pm_')}

    remove = pm_remove | {c.lower() for c in EBI_REMOVE}
    to_drop = [c for c in df.columns if c.lower() in remove]

    return df.drop(columns=to_drop, inplace=False)


def retrieve_metadata(sample_barcodes):
    """Retrieve all sample metadata for the provided barcodes

    Parameters
    ----------
    sample_barcodes : Iterable
        The barcodes to request

    Returns
    -------
    pd.DataFrame
        A DataFrame representation of the sample metadata.
    list of dict
        A report of the observed errors in the metadata pulldown. The dicts
        are composed of {"barcode": list of str | str, "error": str}.
    """
    error_report = []

    dups, errors = _find_duplicates(sample_barcodes)
    if errors is not None:
        error_report.append(errors)

    fetched = []
    for sample_barcode in set(sample_barcodes):
        bc_md, errors = _fetch_barcode_metadata(sample_barcode)
        if errors is not None:
            error_report.append(errors)
            continue

        fetched.append(bc_md)

    df = pd.DataFrame()
    if len(fetched) == 0:
        error_report.append({"error": "No metadata was obtained"})
    else:
        survey_templates, st_errors = _fetch_observed_survey_templates(fetched)
        if st_errors is not None:
            error_report.append(st_errors)
        else:
            df = _to_pandas_dataframe(fetched, survey_templates)

    return df, error_report


def _fetch_observed_survey_templates(sample_metadata):
    """Determine which templates to obtain and then fetch

    Parameters
    ----------
    sample_metadata : list of dict
        Each element corresponds to the structure obtained from
        _fetch_barcode_metadata

    Returns
    -------
    dict
        The survey template IDs as keys, and the Vue form representation of
        each survey
    dict or None
        Any error information associated with the retreival. If an error is
        observed, the survey responses should not be considered valid.
    """
    errors = {}

    templates = {}
    for bc_md in sample_metadata:
        account_id = bc_md['account']['id']
        source_id = bc_md['source']['id']
        observed_templates = {s['template'] for s in bc_md['survey_answers']}

        # it doesn't matter which set of IDs we use but they need to be valid
        # for the particular survey template
        for template_id in observed_templates:
            if template_id not in templates:
                templates[template_id] = {'account_id': account_id,
                                          'source_id': source_id}

    surveys = {}
    for template_id, ids in templates.items():
        survey, error = _fetch_survey_template(template_id, ids)
        if error:
            errors[template_id] = error
        else:
            surveys[template_id] = survey

    return surveys, errors if errors else None


def _fetch_survey_template(template_id, ids):
    """Fetch the survey structure to get full multi-choice detail

    Parameters
    ----------
    template_id : int
        The survey template ID to fetch
    ids : dict
        An account and source ID to use

    Returns
    -------
    dict
        The survey structure as returned from the private API
    dict or None
        Any error information associated with the retreival. If an error is
        observed, the survey responses should not be considered valid.
    """
    errors = None

    ids['template_id'] = template_id
    url = ("/api/accounts/%(account_id)s/sources/%(source_id)s/"
           "survey_templates/%(template_id)d?language_tag=en-US")

    status, response = APIRequest.get(url % ids)
    if status != 200:
        errors = {"ids": ids,
                  "error": str(status) + " from api"}

    return response, errors


def _to_pandas_dataframe(metadatas, survey_templates):
    """Convert the raw barcode metadata into a DataFrame

    Parameters
    ----------
    metadatas : list of dict
        The raw metadata obtained from the private API
    survey_templates : dict
        Raw survey template data for the surveys represented by
        the metadatas

    Returns
    -------
    pd.DataFrame
        The fully constructed sample metadata
    """
    transformed = []

    multiselect_map = _construct_multiselect_map(survey_templates)
    for metadata in metadatas:
        as_series = _to_pandas_series(metadata, multiselect_map)
        transformed.append(as_series)

    df = pd.DataFrame(transformed)
    df.index.name = 'sample_name'

    # fill in any other nulls that may be present in the frame
    # as could happen if not all individuals took all surveys
    df.fillna('Missing: not provided', inplace=True)

    return df


def _to_pandas_series(metadata):
    """Convert the sample metadata object from the private API to a pd.Series

    Parameters
    ----------
    metadata : dict
        The response object from a query to fetch all sample metadata for a
        barcode.

    Returns
    -------
    pd.Series
        The transformed responses
    set
        Observed multi-selection responses
    """
    name = metadata['sample_barcode']
    hsi = metadata['host_subject_id']
    source_type = metadata["source_type"]

    sample_detail = metadata['sample']
    collection_timestamp = sample_detail['datetime_collected']

    if source_type == 'human':
        sample_type = sample_detail['site']
        sample_invariants = HUMAN_SITE_INVARIANTS[sample_type]
    elif source_type == 'animal':
        sample_type = sample_detail['site']
        sample_invariants = {}
    else:
        sample_type = sample_detail['source']['description']
        sample_invariants = {}

    values = [hsi, collection_timestamp]
    index = ['HOST_SUBJECT_ID', 'COLLECTION_TIMESTAMP']

    # TODO: denote sample projects
    observed_multiselect = set()
    for survey in metadata['survey_answers']:
        for shortname, answer in survey['response'].values():
            if isinstance(answer, list):
                for selection in answer:
                    specific_shortname = _build_col_name(shortname, selection)
                    values.append('true')
                    index.append(specific_shortname)
                    observed_multiselect.add(specific_shortname)
            else:
                values.append(answer)
                index.append(shortname)

    for variable, value in sample_invariants.items():
        index.append(variable)
        values.append(value)

    return pd.Series(values, index=index, name=name), observed_multiselect


def _fetch_barcode_metadata(sample_barcode):
    """Query the private API to obtain per-sample metadata

    Parameters
    ----------
    sample_barcode : str
        The barcode to request

    Returns
    -------
    dict
        The survey responses associated with the sample barcode
    dict or None
        Any error information associated with the retreival. If an error is
        observed, the survey responses should not be considered valid.
    """
    errors = None

    status, response = APIRequest.get(
        '/api/admin/metadata/samples/%s/surveys/' % sample_barcode
    )
    if status != 200:
        errors = {"barcode": sample_barcode,
                  "error": str(status) + " from api"}

    return response, errors


def _build_col_name(col_name, multiselect_answer):
    """For a multiselect response, form a stable metadata variable name

    Parameters
    ----------
    col_name : str
        The basename for the column which would correspond to the question.
    multiselect_answer : str
        The selected answer

    Returns
    -------
    str
        The formatted column name, For example, in the primary survey
        there is a multiple select option for alcohol which includes beer
        and wine. The basename would be "alcohol", one multiselect_answer
        would be "beer", and the formatted column name would be
        "alcohol_beer".

    Raises
    ------
    ValueError
        If there are removed characters as it may create an unsafe column name.
        For example, "A+" and "A-" for blood types would both map to "A".
    """
    # replace spaces with _
    multiselect_answer = multiselect_answer.replace(' ', '_')

    # remove any non-alphanumeric character (except for _)
    reduced = re.sub('[^0-9a-zA-Z_]+', '', multiselect_answer)
    if multiselect_answer != reduced:
        raise ValueError("An unsafe column name was build: "
                         "%s -> %s" % (multiselect_answer, reduced))

    return f"{col_name}_{multiselect_answer}"


def _find_duplicates(barcodes):
    """Report any barcode observed more than a single time

    Parameters
    ----------
    barcodes : iterable of str
        The barcodes to check for duplicates in

    Returns
    -------
    set
        Any barcode observed more than a single time
    dict
        Any error information or None
    """
    error = None
    counts = Counter(barcodes)
    dups = {barcode for barcode, count in counts.items() if count > 1}

    if len(dups) > 0:
        error = {
            "barcode": list(dups),
            "error": "Duplicated barcodes in input"
        }

    return dups, error
