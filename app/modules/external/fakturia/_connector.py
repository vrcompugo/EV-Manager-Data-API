import requests
import base64

from app.modules.settings import get_settings


def get(url, parameters=None):
    config = get_settings("external/fakturia")
    token = config["api-key"]

    if token is not None:
        response = requests.get(
            config["url"] + url,
            headers={'api-key': token},
            params=parameters
        )
        try:
            return response.json()
        except Exception as e:
            print(response.text)
    return {}


def post(url, post_data=None, files=None):

    config = get_settings("external/fakturia")
    token = config["api-key"]

    response = requests.post(
        config["url"] + url,
        json=post_data,
        headers={
            'api-key': token,
            'accept': 'application/json'
        }
    )
    try:
        data = response.json()
        return data
    except Exception as e:
        print("error1", response.text)


def put(url, post_data=None, files=None):

    config = get_settings("external/fakturia")
    token = config["api-key"]

    response = requests.put(
        config["url"] + url,
        json=post_data,
        headers={
            'api-key': token,
            'accept': 'application/json'
        }
    )
    try:
        data = response.json()
        return data
    except Exception as e:
        print("error1", response.text)
