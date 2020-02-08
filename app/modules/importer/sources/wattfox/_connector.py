import requests
import base64

from app.modules.settings.settings_services import get_one_item

config = get_one_item("importer/wattfox")


def authenticate():
    if config is None:
        print("no config for wattfox")
        return None
    response = requests.post(config["data"]["url"] + "/login",
                             data={
                                 "user": config["data"]["username"],
                                 "pass": config["data"]["password"]}
                             )
    if response.status_code == 200:
        data = response.json()
        if "auth_token" in data:
            return data["auth_token"]
        else:
            print(data)
    else:
        print(response.text)
    return None


def get(url, parameters=None):

    token = authenticate()

    if token is not None:
        response = requests.get(
            config["data"]["url"] + url,
            headers={'X-AUTH-TOKEN': token},
            params=parameters
        )
        try:
            return response.json()
        except Exception as e:
            print(response.text)
    return None
