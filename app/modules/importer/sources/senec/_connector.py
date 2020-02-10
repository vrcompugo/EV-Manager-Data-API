import requests
import base64

from app.modules.settings.settings_services import get_one_item

config = get_one_item("importer/senec")


def authenticate():
    if config is None:
        print("no config for senec")
        return None
    response = requests.post(config["data"]["url"] + "/API/auth",
                             data={
                                 "username": config["data"]["username"],
                                 "password": config["data"]["password"]}
                             )

    if response.status_code == 200:
        data = response.json()
        if "token" in data:
            return data["token"]
    return None


def get(url, parameters=None):

    token = authenticate()

    if token is not None:
        response = requests.get(
            config["data"]["url"] + url,
            headers={'Authorization': "Bearer {}".format(token)},
            params=parameters
        )

        try:
            return response.json()
        except Exception as e:
            print(response.text)
    return None
