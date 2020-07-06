import requests
import base64

from app.modules.settings.settings_services import get_one_item

config = get_one_item("importer/aroundhome")


def get(url, parameters=None):
    response = requests.get(
        config["data"]["url"] + url,
        headers={
            'X-CLIENT-ID': config["data"]["username"],
            'X-CLIENT-SECRET': config["data"]["password"]
        },
        params=parameters
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


def post(url, parameters=None):
    response = requests.post(
        config["data"]["url"] + url,
        headers={
            'X-CLIENT-ID': config["data"]["username"],
            'X-CLIENT-SECRET': config["data"]["password"]
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
