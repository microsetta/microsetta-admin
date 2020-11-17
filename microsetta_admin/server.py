import jwt
from flask import render_template, Flask, request, session, send_file
import secrets
from datetime import datetime
import io

from jwt import PyJWTError
from werkzeug.exceptions import BadRequest
from werkzeug.utils import redirect
import pandas as pd

from microsetta_admin import metadata_util, upload_util
from microsetta_admin.config_manager import SERVER_CONFIG
from microsetta_admin._api import APIRequest
import importlib.resources as pkg_resources

TOKEN_KEY_NAME = 'token'
SEND_EMAIL_CHECKBOX_DEFAULT_NAME = 'send_email'

PUB_KEY = pkg_resources.read_text(
    'microsetta_admin',
    "authrocket.pubkey")

DUMMY_SELECT_TEXT = '-------'
RECEIVED_TYPE_DROPDOWN = \
    [DUMMY_SELECT_TEXT, "Blood (skin prick)", "Saliva", "Stool",
     "Sample Type Unclear (Swabs Included)"]

VALID_STATUS = "sample-is-valid"
NO_SOURCE_STATUS = "no-associated-source"
NO_ACCOUNT_STATUS = "no-registered-account"
NO_COLLECTION_INFO_STATUS = "no-collection-info"
INCONSISTENT_SAMPLE_STATUS = "sample-has-inconsistencies"
UNKNOWN_VALIDITY_STATUS = "received-unknown-validity"

STATUS_OPTIONS = [DUMMY_SELECT_TEXT, VALID_STATUS, NO_SOURCE_STATUS,
                  NO_ACCOUNT_STATUS, NO_COLLECTION_INFO_STATUS,
                  INCONSISTENT_SAMPLE_STATUS, UNKNOWN_VALIDITY_STATUS]

API_PROJECTS_URL = '/api/admin/projects'


def handle_pyjwt(pyjwt_error):
    # PyJWTError (Aka, anything wrong with token) will force user to log out
    # and log in again
    return redirect('/logout')


def parse_jwt(token):
    """
    Raises
    ------
        jwt.PyJWTError
            If the token is invalid
    """
    decoded = jwt.decode(token, PUB_KEY, algorithms=['RS256'], verify=True)
    return decoded


def build_login_variables():
    # Anything that renders sitebase.html must pass down these variables to
    # jinja2
    token_info = None
    if TOKEN_KEY_NAME in session:
        # If user leaves the page open, the token can expire before the
        # session, so if our token goes back we need to force them to login
        # again.
        token_info = parse_jwt(session[TOKEN_KEY_NAME])

    vars = {
        'endpoint': SERVER_CONFIG["endpoint"],
        'ui_endpoint': SERVER_CONFIG["ui_endpoint"],
        'authrocket_url': SERVER_CONFIG["authrocket_url"]
    }
    if token_info is not None:
        vars['email'] = token_info['email']
    return vars


def build_app():
    # Create the application instance
    app = Flask(__name__)

    flask_secret = SERVER_CONFIG["FLASK_SECRET_KEY"]
    if flask_secret is None:
        print("WARNING: FLASK_SECRET_KEY must be set to run with gUnicorn")
        flask_secret = secrets.token_urlsafe(16)
    app.secret_key = flask_secret
    app.config['SESSION_TYPE'] = 'memcached'
    app.config['SESSION_COOKIE_NAME'] = 'session-microsetta-admin'

    # Set mapping from exception type to response code
    app.register_error_handler(PyJWTError, handle_pyjwt)

    return app


app = build_app()


@app.context_processor
def utility_processor():
    def format_timestamp(timestamp_str):
        if not timestamp_str:
            return "None"
        datetime_obj = datetime.fromisoformat(timestamp_str)
        return datetime_obj.strftime("%Y %B %d  %H:%M:%S")
    return dict(format_timestamp=format_timestamp)


@app.route('/')
def home():
    return render_template('sitebase.html', **build_login_variables())


@app.route('/search', methods=['GET'])
def search():
    return _search()


@app.route('/search/sample', methods=['GET', 'POST'])
def search_sample():
    return _search('samples')


@app.route('/search/kit', methods=['GET', 'POST'])
def search_kit():
    return _search('kit')


@app.route('/search/email', methods=['GET', 'POST'])
def search_email():
    return _search('account')


def _search(resource=None):
    if request.method == 'GET':
        return render_template('search.html', **build_login_variables())
    elif request.method == 'POST':
        query = request.form['search_%s' % resource]

        status, result = APIRequest.get(
                '/api/admin/search/%s/%s' % (resource, query))

        if status == 404:
            result = {'error_message': "Query not found"}
            return render_template('search_result.html',
                                   **build_login_variables(),
                                   result=result), 200
        elif status == 200:
            return render_template('search_result.html',
                                   **build_login_variables(),
                                   resource=resource,
                                   result=result), 200
        else:
            return result


def _translate_nones(a_dict, do_none_to_str):
    # Note: this ISN'T a deep copy. This function is NOT set up
    # for recursing through a multi-layer dictionary
    result = a_dict.copy()
    for k, v in result.items():
        if do_none_to_str and v is None:
            result[k] = ""
        elif not do_none_to_str and v == '':
            result[k] = None
    return result


def _get_projects(include_stats, is_active):
    projects_uri = API_PROJECTS_URL + f"?include_stats={include_stats}"
    if is_active is not None:
        projects_uri += f"&is_active={is_active}"
    status, projects_output = APIRequest.get(projects_uri)

    if status >= 400:
        result = {'error_message': "Unable to load project list."}
    else:
        cleaned_projects = [_translate_nones(x, True) for x in
                            projects_output]
        # if we're not using full project stats, sort
        # alphabetically by project name
        if not include_stats:
            cleaned_projects = sorted(cleaned_projects,
                                      key=lambda k: k['project_name'])
        result = {'projects': cleaned_projects}

    return status, result


@app.route('/manage_projects', methods=['GET', 'POST'])
def manage_projects():
    result = None
    is_active = request.args.get('is_active', None)
    if request.method == 'POST':
        model = {x: request.form[x] for x in request.form}
        project_id = model.pop('project_id')
        model['is_microsetta'] = model.get('is_microsetta', '') == 'true'
        model['bank_samples'] = model.get('bank_samples', '') == 'true'
        model = _translate_nones(model, False)

        if project_id.isdigit():
            # update (put) an existing project
            action = "update"
            status, api_output = APIRequest.put(
                '{}/{}'.format(API_PROJECTS_URL, project_id),
                json=model)
        else:
            # create (post) a new project
            action = "create"
            status, api_output = APIRequest.post(
                API_PROJECTS_URL, json=model)

        # if api post or put failed
        if status >= 400:
            result = {'error_message': f'Unable to {action} project.'}
    # end if post

    # if the above work (if any) didn't produce an error message, return
    # the projects list
    if result is None:
        _, result = _get_projects(include_stats=True, is_active=is_active)

    return render_template('manage_projects.html',
                           **build_login_variables(),
                           result=result), 200


@app.route('/email_stats', methods=['GET', 'POST'])
def email_stats():
    _, result = _get_projects(include_stats=False, is_active=True)
    projects = result.get('projects')
    print("PROJECTS:", projects)

    if request.method == 'GET':
        project = request.args.get('project', None)
        email = request.args.get('email')
        if email is None:
            # They want to search for emails, show them the search dialog
            return render_template("email_stats_pulldown.html",
                                   **build_login_variables(),
                                   resource=None,
                                   search_error=None,
                                   projects=projects)
        emails = [email]
    elif request.method == 'POST':
        project = request.form.get('project', None)
        emails, upload_err = upload_util.parse_request_csv_col(
            request,
            'file',
            'email'
        )
        if upload_err is not None:
            return render_template('email_stats_pulldown.html',
                                   **build_login_variables(),
                                   resource=None,
                                   search_error=[{'error': upload_err}],
                                   projects=projects)
    else:
        raise BadRequest()

    if project == "":
        project = None

    status, result = APIRequest.post(
        '/api/admin/account_email_summary',
        json={
            "emails": emails,
            "project": project
        })

    if status != 200:
        return render_template('email_stats_pulldown.html',
                               search_error=[{'error': result}],
                               resource=None,
                               **build_login_variables(),
                               projects=projects)

    # At a minimum, our table will display these columns.
    # We may show additional info depending on what comes back from the request
    base_data_template = {
        'email': 'XXX',
        'summary': 'XXX',
        'account_id': 'XXX',
        'creation_time': 'XXX',
        'kit_name': 'XXX',
        'project': 'XXX',
        'unclaimed-samples-in-kit': 0,
        'never-scanned': 0,
        'sample-is-valid': 0,
        'no-associated-source': 0,
        'no-registered-account': 0,
        'no-collection-info': 0,
        'sample-has-inconsistencies': 0,
        'received-unknown-validity': 0
    }

    df = pd.DataFrame([base_data_template] + result)
    df = df.drop(0)  # remove the template row
    numeric_cols = [
        "unclaimed-samples-in-kit", "never-scanned", "sample-is-valid",
        "no-associated-source", "no-registered-account", "no-collection-info",
        "sample-has-inconsistencies", "received-unknown-validity"
    ]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)
    df[numeric_cols] = df[numeric_cols].fillna(0)
    # see https://stackoverflow.com/questions/20035518/insert-a-link-inside-a-pandas-table  # noqa
    df['account_id'] = df["account_id"].apply(
        lambda x: '<a ' +
                  'target="_blank" ' +
                  'href="' +
                  SERVER_CONFIG['ui_endpoint'] +
                  '/accounts/' +
                  x +
                  '">' +
                  x +
                  '</a>')
    return render_template("email_stats_pulldown.html",
                           search_error=None,
                           resource=df,
                           **build_login_variables(),
                           projects=projects)


@app.route('/create_kits', methods=['GET', 'POST'])
def new_kits():
    _, result = _get_projects(include_stats=False, is_active=True)
    projects = result.get('projects')

    if request.method == 'GET':
        return render_template('create_kits.html',
                               error_message=result.get('error_message'),
                               projects=projects,
                               **build_login_variables())

    elif request.method == 'POST':
        num_kits = int(request.form['num_kits'])
        num_samples = int(request.form['num_samples'])
        prefix = request.form['prefix']
        selected_project_ids = request.form.getlist('project_ids')
        payload = {'number_of_kits': num_kits,
                   'number_of_samples': num_samples,
                   'project_ids': selected_project_ids}
        if prefix:
            payload['kit_id_prefix'] = prefix

        status, result = APIRequest.post(
                '/api/admin/create/kits',
                json=payload)

        if status != 201:
            return render_template('create_kits.html',
                                   error_message='Failed to create kits',
                                   projects=projects,
                                   **build_login_variables())

        # StringIO/BytesIO based off https://stackoverflow.com/a/45111660
        buf = io.StringIO()
        payload = io.BytesIO()

        # explicitly expand out the barcode detail
        kits = pd.DataFrame(result['created'])
        for i in range(num_samples):
            kits['barcode_%d' % (i+1)] = [r['sample_barcodes'][i]
                                          for _, r in kits.iterrows()]
        kits.drop(columns='sample_barcodes', inplace=True)

        kits.to_csv(buf, sep=',', index=False, header=True)
        payload.write(buf.getvalue().encode('utf-8'))
        payload.seek(0)
        buf.close()

        stamp = datetime.now().strftime('%d%b%Y-%H%M')
        fname = f'kits-{stamp}.csv'

        return send_file(payload, as_attachment=True,
                         attachment_filename=fname,
                         mimetype='text/csv')


def _check_sample_status(extended_barcode_info):
    warning = None
    in_microsetta_project = any(
        [x['is_microsetta'] for x in extended_barcode_info['projects_info']])

    # one warning to rule them all; check in order of precendence
    if not in_microsetta_project:
        warning = UNKNOWN_VALIDITY_STATUS
    elif extended_barcode_info['account'] is None:
        warning = NO_ACCOUNT_STATUS
    elif extended_barcode_info['source'] is None:
        warning = NO_SOURCE_STATUS
    # collection datetime is used as the bellwether for the whole
    # set of sample collection info because it is relevant to all
    # kinds of samples (whereas previously used field, sample site, is not
    # filled when environmental samples are returned).
    elif extended_barcode_info['sample'].get('datetime_collected') is None:
        warning = NO_COLLECTION_INFO_STATUS

    return warning


# Set up handlers for the cases,
#   GET to view the page,
#   POST to update info for a barcode -AND (possibly)-
#        email end user about the change in sample status,
def _scan_get(sample_barcode, update_error):
    # If there is no sample_barcode in the GET
    # they still need to enter one in the box, so show empty page
    if sample_barcode is None:
        return render_template('scan.html', **build_login_variables())

    # Assuming there is a sample barcode, grab that sample's information
    status, result = APIRequest.get(
        '/api/admin/search/samples/%s' % sample_barcode)

    # If we successfully grab it, show the page to the user
    if status == 200:
        # Process result in python because its easier than jinja2.
        status_warning = _check_sample_status(result)

        # check the latest scan to find the default sample_status for form
        latest_status = DUMMY_SELECT_TEXT
        if result['latest_scan']:
            latest_status = result['latest_scan']['sample_status']

        account = result.get('account')
        events = []
        if account:
            event_status, event_result = APIRequest.get(
                '/api/admin/events/accounts/%s' % account['id']
            )
            if event_status != 200:
                raise Exception("Couldn't pull event history")

            events = event_result

        return render_template(
            'scan.html',
            **build_login_variables(),
            barcode_info=result["barcode_info"],
            projects_info=result['projects_info'],
            scans_info=result['scans_info'],
            latest_status=latest_status,
            dummy_status=DUMMY_SELECT_TEXT,
            status_options=STATUS_OPTIONS,
            send_email=session.get(SEND_EMAIL_CHECKBOX_DEFAULT_NAME, True),
            sample_info=result['sample'],
            extended_info=result,
            status_warning=status_warning,
            update_error=update_error,
            received_type_dropdown=RECEIVED_TYPE_DROPDOWN,
            source=result['source'],
            events=events
        )
    elif status == 401:
        # If we fail due to unauthorized, need the user to log in again
        return redirect('/logout')
    elif status == 404:
        # If we fail due to not found, need to tell the user to pick a diff
        # barcode
        return render_template(
            'scan.html',
            **build_login_variables(),
            search_error="Barcode %s Not Found" % sample_barcode,
            update_error=update_error,
            received_type_dropdown=RECEIVED_TYPE_DROPDOWN
        )
    else:
        raise BadRequest()


def _scan_post_update_info(sample_barcode,
                           technician_notes,
                           sample_status,
                           action,
                           issue_type,
                           template,
                           received_type,
                           recorded_type):

    ###
    # Bugfix Part 1 for duplicate emails being sent.  Theory is that client is
    # out of sync due to hitting back button after a scan has changed
    # state.
    # Can't test if client is up to date without ETags, so for right now,
    # we just validate whether or not they should send an email, duplicating
    # the client log.  (This can still break with multiple admin clients,
    # but that is unlikely at the moment.)
    latest_status = None
    # TODO:  Replace this with ETags!
    status, result = APIRequest.get(
        '/api/admin/search/samples/%s' % sample_barcode)

    if result['latest_scan']:
        latest_status = result['latest_scan']['sample_status']
    ###

    # Do the actual update
    status, response = APIRequest.post(
        '/api/admin/scan/%s' % sample_barcode,
        json={
            "sample_status": sample_status,
            "technician_notes": technician_notes
        }
    )

    # if the update failed, keep track of the error so it can be displayed
    if status != 201:
        update_error = response
        return _scan_get(sample_barcode, update_error)
    else:
        update_error = None

    # If we're not supposed to send an email, go back to GET
    if action != "send_email":
        return _scan_get(sample_barcode, update_error)

    ###
    # Bugfix Part 2 for duplicate emails being sent.
    if sample_status == latest_status:
        # This is what we'll hit if javascript thinks it's updating status
        # but is out of sync with the database.
        update_error = "Ignoring Send Email, sample_status would " \
                       "not have been updated (Displayed page was out of " \
                       "sync)"
        return _scan_get(sample_barcode, update_error)
    ###

    # This is what we'll hit if there are no email templates to send for
    # the new sample status (or if we screw up javascript side :D )
    if template is None:
        update_error = "Cannot Send Email: No Issue Type Specified " \
                       "(or no issue types available)"
        return _scan_get(sample_barcode, update_error)

    # Otherwise, send out an email to the end user
    status, response = APIRequest.post(
        '/api/admin/email',
        json={
            "issue_type": issue_type,
            "template": template,
            "template_args": {
                "sample_barcode": sample_barcode,
                "recorded_type": recorded_type,
                "received_type": received_type
            }
        }
    )

    # if the email failed to send, keep track of the error
    # so it can be displayed
    if status != 200:
        update_error = response
    else:
        update_error = None

    return _scan_get(sample_barcode, update_error)


@app.route('/scan', methods=['GET', 'POST'])
def scan():
    # Now that the handlers are set up, parse the request to determine what
    # to do.

    # If its a get, grab the sample_barcode from the query string rather than
    # form parameters
    if request.method == 'GET':
        sample_barcode = request.args.get('sample_barcode')
        return _scan_get(sample_barcode, None)

    # If its a post, make the changes, then refresh the page
    if request.method == 'POST':
        # Without some extra ajax, we can't persist the send_email checkbox
        # until they actually post the form
        send_email = request.form.get('send_email', False)
        session[SEND_EMAIL_CHECKBOX_DEFAULT_NAME] = send_email

        sample_barcode = request.form['sample_barcode']
        technician_notes = request.form['technician_notes']
        sample_status = request.form['sample_status']

        action = request.form.get('action')
        issue_type = request.form.get('issue_type')
        template = request.form.get('template')
        received_type = request.form.get('received_type')
        recorded_type = request.form.get('recorded_type')

        return _scan_post_update_info(sample_barcode,
                                      technician_notes,
                                      sample_status,
                                      action,
                                      issue_type,
                                      template,
                                      received_type,
                                      recorded_type)


@app.route('/metadata_pulldown', methods=['GET', 'POST'])
def metadata_pulldown():
    allow_missing = request.form.get('allow_missing_samples', False)

    if request.method == 'GET':
        sample_barcode = request.args.get('sample_barcode')
        # If there is no sample_barcode in the GET
        # they still need to enter one in the box, so show empty page
        if sample_barcode is None:
            return render_template('metadata_pulldown.html',
                                   **build_login_variables())
        sample_barcodes = [sample_barcode]
    elif request.method == 'POST':
        sample_barcodes, upload_err = upload_util.parse_request_csv_col(
                                                            request,
                                                            'file',
                                                            'sample_name'
        )
        if upload_err is not None:
            return render_template('metadata_pulldown.html',
                                   **build_login_variables(),
                                   search_error=[{'error': upload_err}])
    else:
        raise BadRequest()

    df, errors = metadata_util.retrieve_metadata(sample_barcodes)

    # Strangely, these api requests are returning an html error page rather
    # than a machine parseable json error response object with message.
    # This is almost certainly due to error handling for the cohosted minimal
    # client.  In future, we should just pass down whatever the api says here.
    if len(errors) == 0 or allow_missing:
        df = metadata_util.drop_private_columns(df)

        # TODO:  Streaming direct from pandas is a pain.  Need to search for
        #  better ways to iterate and chunk this file as we generate it
        strstream = io.StringIO()
        df.to_csv(strstream, sep='\t', index=True, header=True)

        # TODO: utf-8 or utf-16 encoding??
        bytestream = io.BytesIO()
        bytestream.write(strstream.getvalue().encode('utf-8'))
        bytestream.seek(0)

        strstream.close()
        return send_file(bytestream,
                         mimetype="text/tab-separated-values",
                         as_attachment=True,
                         attachment_filename="metadata_pulldown.tsv",
                         add_etags=False,
                         cache_timeout=None,
                         conditional=False,
                         last_modified=None,
                         )
    else:

        return render_template('metadata_pulldown.html',
                               **build_login_variables(),
                               info={'barcodes': sample_barcodes},
                               search_error=errors)


@app.route('/authrocket_callback')
def authrocket_callback():
    token = request.args.get('token')
    session[TOKEN_KEY_NAME] = token
    return redirect("/")


@app.route('/logout')
def logout():
    if TOKEN_KEY_NAME in session:
        del session[TOKEN_KEY_NAME]
    return redirect("/")


# If we're running in stand alone mode, run the application
if __name__ == '__main__':
    if SERVER_CONFIG["ssl_cert_path"] and SERVER_CONFIG["ssl_key_path"]:
        ssl_context = (
            SERVER_CONFIG["ssl_cert_path"], SERVER_CONFIG["ssl_key_path"]
        )
    else:
        ssl_context = None

    app.run(
        port=SERVER_CONFIG['port'],
        debug=SERVER_CONFIG['debug'],
        ssl_context=ssl_context
    )
