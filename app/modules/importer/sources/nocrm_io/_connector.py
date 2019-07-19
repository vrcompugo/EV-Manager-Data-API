import requests
import json
import base64

API_URL = "https://kez.nocrm.io/api/v2/"


def authenticate():
    return "3b7be58e5c8a7e38a496f5adafd5062e1ec51502e6d3e281"


def post(url, post_data = None, files=None):

    token = authenticate()

    if token is not None:
        if files is not None:
            response = requests.post(API_URL + format(url),
                                         headers={'X-API-KEY': token},
                                         files=files,
                                         data={})
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
