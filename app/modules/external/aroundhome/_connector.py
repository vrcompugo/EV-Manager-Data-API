import requests
import base64
import json

from app.modules.settings import get_settings


def get(url, parameters=None):
    config = get_settings("external/aroundhome")
    response = requests.get(
        config["url"] + url,
        headers={
            'X-CLIENT-ID': config["username"],
            'X-CLIENT-SECRET': config["password"]
        },
        params=parameters
    )
    try:
        data = response.json()
        if "leads" in data:
            return data["leads"]
        else:
            print("aroundhome error:", parameters, data)
    except Exception as e:
        print("aroundhome:", response.text)


def post(url, parameters=None):
    config = get_settings("external/aroundhome")
    response = requests.post(
        config["url"] + url,
        headers={
            'X-CLIENT-ID': config["username"],
            'X-CLIENT-SECRET': config["password"]
        },
        json=parameters
    )
    try:
        data = response.json()
        if "leads" in data:
            return data["leads"]
        else:
            print(parameters)
            print(data)
    except Exception as e:
        print(response.text)
