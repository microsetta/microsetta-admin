"""Heavily derived from https://github.com/biocore/microsetta-private-api/blob/minimalInterface/microsetta_private_api/example/client_impl.py"""  # noqa

import requests
from microsetta_admin.config_manager import SERVER_CONFIG
from flask import redirect, session
from urllib.parse import urljoin


TOKEN_KEY_NAME = 'token'


class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = "Bearer " + self.token
        return r


class APIRequest:
    API_URL = SERVER_CONFIG["private_api_url"]
    DEFAULT_PARAMS = {'language_tag': 'en-US'}
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
        output = None

        if response.status_code == 401:
            # redirect to home page for login
            output = redirect("/")
        else:
            if response.text:
                output = response.json()

        return response.status_code, output

    @classmethod
    def get(cls, path, params=None):
        response = requests.get(
            urljoin(cls.API_URL, path),
            auth=BearerAuth(session[TOKEN_KEY_NAME]),
            verify=cls.CAfile,
            params=cls.build_params(params))

        return cls._check_response(response)

    @classmethod
    def put(cls, path, params=None, json=None):
        response = requests.put(
            urljoin(cls.API_URL, path),
            auth=BearerAuth(session[TOKEN_KEY_NAME]),
            verify=cls.CAfile,
            params=cls.build_params(params),
            json=json)

        return cls._check_response(response)

    @classmethod
    def post(cls, path, params=None, json=None):
        response = requests.post(
            urljoin(cls.API_URL, path),
            auth=BearerAuth(session[TOKEN_KEY_NAME]),
            verify=cls.CAfile,
            params=cls.build_params(params),
            json=json)
        return cls._check_response(response)
