import requests
import base64

from app.modules.settings import get_settings


def post(url, parameters=None):
    config = get_settings("external/hausfrage")
    parameters["Debug"] = True
    parameters["Username"] = config["username"]
    parameters["Password"] = config["password"]
    response = requests.post(
        config["url"] + url,
        json=parameters
    )
    try:
        data = response.json()
        if "IsSuccessful" in data and data["IsSuccessful"]:
            if "Leads" in data:
                return data["Leads"]
        else:
            print(parameters)
            print(data)
    except Exception as e:
        print(response.text)
