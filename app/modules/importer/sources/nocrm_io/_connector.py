import requests
import os
import base64

from app.modules.settings.settings_services import get_one_item


API_URL = os.getenv('IMPORT_NOCRM_API', "https://kez.nocrm.io/api/v2/")

config = get_one_item("importer/nocrm_io")
remote_user_id = config["data"]["bot_user_id"]


def authenticate():
    return config["data"]["api_key"]


def post(url, post_data = None, files=None):

    token = authenticate()

    if token is not None:
        if files is not None:
            response = requests.post(API_URL + format(url),
                                         headers={'X-API-KEY': token},
                                         files=files,
                                         data=post_data)
        else:
            response = requests.post(API_URL + format(url),
                                     headers={'X-API-KEY': token},
                                     json=post_data)
        try:
            return response.json()
        except:
            print(response.text)
    return {}


def put(url, post_data = None):

    token = authenticate()

    if token is not None:
        response = requests.put(API_URL + format(url),
                                     headers={'X-API-KEY': token},
                                     json=post_data)
        try:
            return response.json()
        except:
            print(response.text)
    return {}


def get(url, parameters=None):

    token = authenticate()

    if token is not None:
        response = requests.get(API_URL + format(url),
                                params=parameters,
                                headers={'X-API-KEY': token})
        try:
            return response.json()
        except:
            print(response.text)
    return {}
