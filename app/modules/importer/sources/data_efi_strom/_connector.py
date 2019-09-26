import requests
import json
import base64
import os

from app.modules.settings.settings_services import get_one_item

API_URL = os.getenv('IMPORT_DATA_EFI_STROM_API', "https://data.efi-strom.de")
config = get_one_item("importer/data.efi-strom.de")


def authenticate():
    response = requests.get(API_URL + "/AuthToken",
                            auth=(config["data"]["api_user"], config["data"]["api_password"]))
    if response.status_code == 200:

        data = json.loads(response.text)
        if "token" in data:
            token = data["token"] + ":"
            return str(base64.b64encode(bytes(token, encoding="utf8"))).strip("b'")
    return None


def post(url, post_data = None):

    token = authenticate()

    if token is not None:
        response = requests.post(API_URL + "/v1/{}".format(url),
                                     headers={'Authorization': "Basic {}".format(token)},
                                     json=post_data)
        try:
            return response.json()
        except:
            print(response.text)
    return {}


def get(url, parameters=None, raw=False):

    token = authenticate()

    if token is not None:
        response = requests.get(API_URL + "/v1/{}".format(url),
                                     headers={'Authorization': "Basic {}".format(token)},
                                     params=parameters)
        try:
            if raw:
                return response
            return response.json()
        except:
            print(response.text)
    return {}