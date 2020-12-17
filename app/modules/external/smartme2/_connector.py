import requests
import base64
from requests.auth import HTTPBasicAuth

from app.modules.settings import get_settings


def get(url, parameters=None):

    config = get_settings("external/smartme2")

    response = requests.get(
        config["url"] + url,
        auth=HTTPBasicAuth(config["username"], config["password"]),
        params=parameters
    )
    try:
        data = response.json()
        return data
    except Exception as e:
        print(response.text)
