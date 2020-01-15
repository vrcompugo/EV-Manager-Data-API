import requests
import base64

from app.modules.settings.settings_services import get_one_item

config = get_one_item("importer/daa")


def authenticate():
    if config is None:
        print("no config for daa")
        return None
    token = config["data"]["username"] + ":" + config["data"]["password"]
    return str(base64.b64encode(bytes(token, encoding="utf8"))).strip("b'")


def get(url, parameters=None):

    token = authenticate()

    if token is not None:
        response = requests.get(
            config["data"]["url"] + url,
            headers={'Authorization': "Basic {}".format(token)},
            params=parameters
        )
        try:
            return response.json()
        except Exception as e:
            print(response.text)
    return {}
