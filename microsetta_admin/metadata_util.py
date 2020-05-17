from microsetta_admin._api import APIRequest
from collections import defaultdict, Counter
import re


# TODO: If this needs to be able to handle every barcode in the system at once
#  we will need to refactor to iterate over barcodes and append to some file.
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
    cached_templates = {}
    cached_response_json = defaultdict(list)
    barcode_to_host_sub_id = {}
    error_report = []

    dups = _find_duplicates(sample_barcodes)
    if len(dups) > 0:
        error_report.append({
            "barcode": list(dups),
            "error": "Duplicated barcodes in input"
        })

    for sample_barcode in sample_barcodes:
        barcode_metadata, errors = _fetch_barcode_metadata(sample_barcode)
        if errors is not None:
            error_report.append(errors)
            continue

        barcode_to_host_sub_id[sample_barcode] = response["host_subject_id"]
        for answer in response["survey_answers"]:
            if answer["template"] not in cached_templates:
                template_status, template_response = APIRequest.get(
                    '/api/accounts/%s'
                    '/sources/%s'
                    '/survey_templates/%s' %
                    (response["account"]["id"],
                     response["source"]["id"],
                     answer["template"]))
                if template_status == 200:
                    cached_templates[answer["template"]] = template_response
                else:
                    # Mark an error and prevent future attempts to grab the
                    # the survey template
                    error_report.append({
                        "barcode": sample_barcode,
                        "template": answer["template"],
                        "error": str(template_status) + " from api"})
                    cached_templates[answer["template"]] = None
                    continue

            cached_response_json[sample_barcode].append(answer)

    multiselect_map = _build_values_per_question(cached_templates)
    transformed_response = defaultdict(dict)

    for barcode in cached_response_json:
        transformed_response[barcode]["host_subject_id"] = \
            barcode_to_host_sub_id[barcode]
        for survey_answers in cached_response_json[barcode]:
            for q_id in survey_answers['response']:
                col_name = survey_answers["response"][q_id][0]
                answer = survey_answers["response"][q_id][1]
                if isinstance(answer, list):
                    answer_set = {a: False for a in answer}
                    for possible_answer in multiselect_map[q_id]:
                        multi_col_name = _build_col_name(col_name,
                                                         possible_answer)
                        if multi_col_name in transformed_response[barcode]:
                            error_report.append({
                                "barcode": barcode,
                                "error": "Duplicate response to question " +
                                         str(q_id) + "/" + str(col_name)
                            })
                        else:
                            transformed_response[barcode][multi_col_name] = \
                                possible_answer in answer_set
                            answer_set[possible_answer] = True
                    for a in answer_set:
                        if not answer_set[a]:
                            error_report.append({
                                "barcode": barcode,
                                "error": "Invalid response to question " +
                                         str(q_id) + "/" + str(col_name)
                            })
                else:
                    if col_name in transformed_response[barcode]:
                        error_report.append({
                            "barcode": barcode,
                            "error": "Duplicate response to question " +
                                     str(q_id) + "/" + str(col_name)
                        })
                    else:
                        transformed_response[barcode][col_name] = answer

    # print("TEMPLATES")
    # print(json.dumps(cached_templates, indent=2))
    # print("RESPONSES")
    # print(json.dumps(cached_response_json, indent=2))
    # print("TEMPLATE POSSIBLE MULTISELECT OPTIONS")
    # print(json.dumps(multiselect_map, indent=2))
    # print("TRANSFORMED")
    # print(json.dumps(transformed_response, indent=2))
    # print("ERRORS")
    # print(json.dumps(error_report, indent=2))

    return transformed_response, error_report


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


def _build_values_per_question(templates):
    final_map = {}

    def visit_field(map, field):
        if field["type"] == "checklist":
            final_map[field["id"]] = field["values"]

    for template_id in templates:
        template = templates[template_id]
        if template["survey_template_text"]["fields"]:
            for field in template["survey_template_text"]["fields"]:
                visit_field(final_map, field)
        for group in template["survey_template_text"]["groups"]:
            for field in group["fields"]:
                visit_field(final_map, field)

    return final_map


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
