import jwt
from flask import render_template, Flask, request, session
import secrets

from werkzeug.utils import redirect

from microsetta_admin.config_manager import SERVER_CONFIG
from microsetta_admin._api import APIRequest
import importlib.resources as pkg_resources


TOKEN_KEY_NAME = 'token'

PUB_KEY = pkg_resources.read_text(
    'microsetta_admin',
    "authrocket.pubkey")


def parse_jwt(token):
    decoded = jwt.decode(token, PUB_KEY, algorithms=['RS256'], verify=True)
    return decoded


def build_login_variables():
    # Anything that renders sitebase.html must pass down these variables to
    # jinja2
    token_info = None
    if TOKEN_KEY_NAME in session:
        try:
            # If user leaves the page open, the token can expire before the
            # session, so if our token goes back we need to force them to login
            # again.
            token_info = parse_jwt(session[TOKEN_KEY_NAME])
        except jwt.exceptions.ExpiredSignatureError:
            return redirect('/logout')

    vars = {
        'endpoint': SERVER_CONFIG["endpoint"],
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

    return app


app = build_app()


@app.route('/')
def home():
    return render_template('sitebase.html', **build_login_variables())


@app.route('/search', methods=['GET', 'POST'])
def search_result():
    if request.method == 'GET':
        return render_template('search.html', **build_login_variables())
    elif request.method == 'POST':
        query = request.form['search_term']

        status, result = APIRequest.get(
                '/api/admin/search/samples/%s' % query)

        if result['kit'] is None:
            # a sample has to be associated with a kit, so if there is no kit
            # then the sample doesn't exist
            result['error_message'] = '%s not found' % query

        if status == 200:
            return render_template('search_result.html',
                                   **build_login_variables(),
                                   result=result), 200
        else:
            return result


@app.route('/create')
def new_kits():
    return render_template('create.html', **build_login_variables())


def _check_sample_status(extended_barcode_info):
    # TODO:  What are the error conditions we need to know about a barcode?
    warnings = []
    if extended_barcode_info['account'] is None:
        warnings.append("No associated account")
    if extended_barcode_info['source'] is None:
        warnings.append("No associated source")
    if extended_barcode_info['sample'] is None:
        warnings.append("No associated sample")
    elif extended_barcode_info['sample']['site'] is None:
        warnings.append("Sample site not specified")

    return warnings


@app.route('/scan', methods=['GET', 'POST'])
def scan():
    update_error = None
    sample_barcode = None

    # If its a get, grab the sample_barcode from the query string rather than
    # form parameters
    if request.method == 'GET':
        sample_barcode = request.args.get('sample_barcode')
        # If there is no sample_barcode in the GET
        # they still need to enter one in the box, so show empty page
        if sample_barcode is None:
            return render_template('scan.html', **build_login_variables())

    # If its a post, make the changes, then refresh the page
    if request.method == 'POST':
        sample_barcode = request.form['sample_barcode']
        technician_notes = request.form['technician_notes']
        sample_status = request.form['sample_status']

        # Do the actual update
        status, response = APIRequest.post(
            '/api/admin/scan/%s' % sample_barcode,
            json={
                "sample_status": sample_status,
                "technician_notes": technician_notes
            }
        )

        # if the update failed, keep track of the error
        if status != 201:
            update_error = response

    # Now, whether its a post or a get, gather up the model objects to show
    # all the data to the user.

    # Grab the sample information
    status, result = APIRequest.get(
        '/api/admin/search/samples/%s' % sample_barcode)

    # If we successfully grab it, show the page to the user
    if status == 200:
        # Process result in python because its easier than jinja2.
        status_warnings = _check_sample_status(result)
        # sample_info may be None if barcode not in agp, then no sample_site
        # available
        sample_info = result['sample']
        return render_template(
            'scan.html',
            **build_login_variables(),
            info=result['barcode_info'],
            sample_info=sample_info,
            extended_info=result,
            status_warnings=status_warnings,
            update_error=update_error
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
            update_error=update_error
        )


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
