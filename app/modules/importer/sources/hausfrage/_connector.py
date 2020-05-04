import requests
import base64

from app.modules.settings.settings_services import get_one_item

config = get_one_item("importer/hausfrage")


def post(url, parameters=None):
    parameters["Debug"] = True
    parameters["Username"] = config["data"]["username"]
    parameters["Password"] = config["data"]["password"]
    response = requests.post(
        config["data"]["url"] + url,
        json=parameters
    )
    try:
        data = response.json()
        if "isSuccessful" in data and data["isSuccessful"]:
            return data
        else:
            print(parameters)
            print(data)
    except Exception as e:
        print(response.text)
