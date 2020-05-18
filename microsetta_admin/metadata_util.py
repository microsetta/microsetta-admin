from microsetta_admin._api import APIRequest
from collections import defaultdict, Counter
import re
import pandas as pd


def retrieve_metadata(sample_barcodes, remove_columns_for_ebi):
    """Retrieve all sample metadata for the provided barcodes

    Parameters
    ----------
    sample_barcodes : Iterable
        The barcodes to request
    remove_columns_for_ebi : boolean
        If True, remove columns of data that cannot be submitted to EBI.

    Returns
    -------
    pd.DataFrame
        A DataFrame representation of the sample metadata.
    list of dict
        A report of the observed errors in the metadata pulldown. The dicts
        are composed of {"barcode": list of str | str, "error": str}.
    """
    error_report = []

    dups = _find_duplicates(sample_barcodes)
    if len(dups) > 0:
        error_report.append({
            "barcode": list(dups),
            "error": "Duplicated barcodes in input"
        })

    transformed = []
    multiselects = set()
    for sample_barcode in sample_barcodes:
        barcode_metadata, errors = _fetch_barcode_metadata(sample_barcode)

        if errors is not None:
            error_report.append(errors)
            continue

        as_series, observed_multiselect = _to_pandas_series(barcode_metadata)

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

    return df, errors


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

    values = [hsi]
    index = ['HOST_SUBJECT_ID']

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
    """
    counts = Counter(barcodes)
    return {barcode for barcode, count in counts.items() if count > 1}
