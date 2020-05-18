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
        barcode_metadata, errors = _fetch_barcode_metadata(sample_barcode)
        import json
        print(json.dumps(barcode_metadata, indent=2))
        if errors is not None:
            error_report.append(errors)
            continue

        fetched.append(barcode_metadata)

    if len(fetched) == 0:
        error_report.append({"error": "No metadata was obtained"})
        df = pd.DataFrame()
    else:
        df = _to_pandas_dataframe(fetched)

    return df, error_report


def _to_pandas_dataframe(metadatas):
    """Convert the raw barcode metadata into a DataFrame

    Parameters
    ----------
    metadatas : list of dict
        The raw metadata obtained from the private API

    Returns
    -------
    pd.DataFrame
        The fully constructed sample metadata
    """
    transformed = []
    multiselects = set()

    for metadata in metadatas:
        as_series, observed_multiselect = _to_pandas_series(metadata)
        transformed.append(as_series)
        multiselects.update(observed_multiselect)

    df = pd.DataFrame(transformed)
    df.index.name = 'sample_name'

    # update reponse where someone did not check a multi-select box
    for multiselect in multiselects:
        nulls = df[multiselect].isnull()
        df.loc[nulls, multiselect] = 'false'

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
    """
    # replace spaces with _
    multiselect_answer = multiselect_answer.replace(' ', '_')

    # remove any non-alphanumeric character (except for _)
    multiselect_answer = re.sub('[^0-9a-zA-Z_]+', '', multiselect_answer)
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
