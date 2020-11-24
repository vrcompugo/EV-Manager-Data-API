import requests
import base64

from app.modules.settings import get_settings


def authenticate():
    config = get_settings("external/daa")
    if config is None:
        print("no config for daa")
        return None
    token = config["username"] + ":" + config["password"]
    return str(base64.b64encode(bytes(token, encoding="utf8"))).strip("b'")


def get(url, parameters=None):
    config = get_settings("external/daa")
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
