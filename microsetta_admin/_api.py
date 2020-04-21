"""Heavily derived from https://github.com/biocore/microsetta-private-api/blob/minimalInterface/microsetta_private_api/example/client_impl.py"""  # noqa

from ._model import Sample
import requests
from microsetta_admin.config_manager import SERVER_CONFIG
from flask import redirect, render_template, session
from urllib.parse import quote


TOKEN_KEY_NAME = 'token'


class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = "Bearer " + self.token
        return r


class APIRequest:
    API_URL = SERVER_CONFIG["private_api_url"]
    DEFAULT_PARAMS = {} # {'language_tag': 'en-US'}
    CAfile = SERVER_CONFIG["CAfile"]

    @classmethod
    def build_params(cls, params):
        all_params = {}
        for key in cls.DEFAULT_PARAMS:
            all_params[key] = cls.DEFAULT_PARAMS[key]

        all_params.update({} if params is None else params)
        return all_params

    @staticmethod
    def _check_response(response):
        do_return = True
        output = None

        if response.status_code == 401:
            # redirect to home page for login
            output = redirect("/")
        elif response.status_code >= 400:
            # redirect to general error page
            error_txt = quote(response.text)
            mailto_url = "mailto:{0}?subject={1}&body={2}".format(
                "microsetta@ucsd.edu", quote("admin interface error"),
                error_txt)

            output = render_template('error.html',
                                     mailto_url=mailto_url,
                                     error_msg=response.text)
        else:
            do_return = False
            if response.text:
                output = response.json()

        return do_return, output

    def get_mock(self, url):
        # TODO: replace mock with real stuff...
        if 'search/samples' in url:
            if '000004216' in url:
                mock = Sample('d8592c74-9699-2135-e040-8a80115d6401',
                              '2013-10-15 09:30:00', 'Stool', 'stuff',
                              '000004216', '2013-10-16',
                              ['American Gut Project'])
                return (mock.to_api(), 200)
            else:
                return ({}, 404)
        else:
            return ({}, 404)

    @classmethod
    def get(cls, path, params=None):
        response = requests.get(
            cls.API_URL + path,
            auth=BearerAuth(session[TOKEN_KEY_NAME]),
            verify=cls.CAfile,
            params=cls.build_params(params))

        return cls._check_response(response)

    @classmethod
    def put(cls, path, params=None, json=None):
        response = requests.put(
            cls.API_URL + path,
            auth=BearerAuth(session[TOKEN_KEY_NAME]),
            verify=cls.CAfile,
            params=cls.build_params(params),
            json=json)

        return cls._check_response(response)

    @classmethod
    def post(cls, path, params=None, json=None):
        response = requests.post(
            cls.API_URL + path,
            auth=BearerAuth(session[TOKEN_KEY_NAME]),
            verify=cls.CAfile,
            params=cls.build_params(params),
            json=json)

        return cls._check_response(response)
