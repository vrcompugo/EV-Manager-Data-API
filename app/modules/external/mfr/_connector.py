import requests
import base64

from app.modules.settings import get_settings


def authenticate():
    config = get_settings("external/mfr")
    if config is None:
        print("no config for mfr")
        return None
    token = config["username"] + ":" + config["password"]
    return str(base64.b64encode(bytes(token, encoding="utf8"))).strip("b'")


def get(url, parameters=None):
    config = get_settings("external/mfr")
    token = authenticate()

    if token is not None:
        response = requests.get(
            config["url"] + url,
            headers={'Authorization': "Basic {}".format(token)},
            params=parameters
        )
        try:
            return response.json()
        except Exception as e:
            print(response.text)
    return {}


def get_download(url, parameters=None):
    config = get_settings("external/mfr")
    token = authenticate()

    if token is not None:
        response = requests.get(
            "https://portal.mobilefieldreport.com" + url,
            headers={'Authorization': "Basic {}".format(token)},
            params=parameters
        )
        try:
            return response
        except Exception as e:
            print(response.text)
    return {}


def post(url, post_data=None, files=None, type=None):
    config = get_settings("external/mfr")
    base_url = config["url"]
    token = authenticate()

    if token is not None:
        if type is not None and type == "mfr":
            base_url = base_url.replace("/odata", "/mfr")
        if files is not None:
            base_url = base_url + url
            response = requests.post(
                base_url,
                files=files,
                headers={
                    'Authorization': "Basic {}".format(token),
                    'accept': 'application/json'
                }
            )
        else:
            base_url = base_url + url
            response = requests.post(
                base_url,
                json=post_data,
                headers={
                    'Authorization': "Basic {}".format(token),
                    'accept': 'application/json'
                }
            )
        try:
            return response.json()
        except Exception as e:
            print(response.text)
    return {}


def put(url, post_data=None, files=None, type=None):
    config = get_settings("external/mfr")
    base_url = config["url"]
    token = authenticate()

    if token is not None:
        if type is not None and type == "mfr":
            base_url = base_url.replace("/odata", "/mfr")

        base_url = base_url + url

        response = requests.put(
            base_url,
            json=post_data,
            headers={
                'Authorization': "Basic {}".format(token),
                'accept': 'application/json'
            }
        )
        try:
            return response.json()
        except Exception as e:
            print(response.text)
    return {}
