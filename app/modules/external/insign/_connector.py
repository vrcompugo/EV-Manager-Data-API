import requests
import base64

from app.modules.settings import get_settings


def authenticate():
    config = get_settings("external/insign")
    if config is None:
        print("no config for insign")
        return None
    token = config["username"] + ":" + config["password"]
    return str(base64.b64encode(bytes(token, encoding="utf8"))).strip("b'")


def get(url, parameters=None, as_binary=False):
    config = get_settings("external/insign")
    token = authenticate()

    if token is not None:
        response = requests.get(
            config["url"] + url,
            headers={'Authorization': "Basic {}".format(token)},
            params=parameters
        )
        try:
            if as_binary:
                return response.content
            return response.json()
        except Exception as e:
            print(response.text)
    return {}


def post(url, post_data=None, params=None, files=None):
    config = get_settings("external/insign")

    token = authenticate()

    if token is not None:
        response = requests.post(
            config["url"] + url,
            json=post_data,
            files=files,
            params=params,
            headers={'Authorization': "Basic {}".format(token)}
        )
        try:
            data = response.json()
            return data
        except Exception as e:
            print(e)
            print("error1", response.text)
    return {}