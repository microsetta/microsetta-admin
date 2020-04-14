from flask import render_template, session, redirect, Flask, request
import secrets
from microsetta_admin.config_manager import SERVER_CONFIG
from microsetta_admin._api import APIRequest


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
    return render_template('sitebase.html')


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'GET':
        return render_template('search.html')
    else:
        query = request.form['search_term']

        barcode_result, barcode_status = APIRequest.get('/.../barcode/%s' % query)
        name_result, name_status = APIRequest.get('/.../name/%s' % query)
        kitid_result, kitid_status = APIRequest.get('/.../kitid/%s' % query)

        error = False
        if barcode_status == 200:
            result = barcode_result
        elif name_status == 200:
            result = name_result
        elif kitid_status == 200:
            result = kitid_result
        else:
            error = True
            result = {'message': 'Nothing was found.'}

        return render_template('search_result.html',
                               result=result,
                               error=error)


@app.route('/create')
def new_kits():
    return render_template('create.html')


@app.route('/scan')
def scan():
    return render_template('scan.html')


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

