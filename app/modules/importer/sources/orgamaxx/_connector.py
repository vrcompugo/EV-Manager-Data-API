import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import os

from app.modules.settings.settings_services import get_one_item

API_URL = os.getenv('IMPORT_ORGAMAXX_API', "https://2ei3scwibnc5bkfm.myfritz.net:5000/v1/")
config = get_one_item("importer/orgamaxx")


def authenticate():
    response = requests.post(
        API_URL + "login",
        json={
            "USER": config["data"]["api_user"],
            "PASSWORD": config["data"]["api_password"]
        },
        verify=False
    )
    if response.status_code == 200:
        data = response.json()
        if "Authorization" in data:
            return data["Authorization"]

    return None


def post(url, post_data = None):

    token = authenticate()

    if token is not None:
        response = requests.post(API_URL + url,
                                 headers={'Authorization': token},
                                 json=post_data,
                                 verify=False)
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
                                 headers={'Authorization': token},
                                 verify=False)
        try:
            return response.json()
        except:
            print(response.text)
    return {}
