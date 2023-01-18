import requests
import base64

from app.modules.settings import get_settings


def authenticate():
    config = get_settings("external/wattfox")
    if config is None:
        print("no config for wattfox")
        return None
    response = requests.post(config["url"] + "/login",
                             json={
                                "user": config["username"],
                                "pass": config["password"]}
                             )
    print("wattfox auth", response.status_code, response.text)
    if response.status_code == 200:
        data = response.json()
        if "auth_token" in data:
            return data["auth_token"]
        else:
            print("wattfox data", data)
    else:
        print("wattfox error1", response.text)
    return None


def get(url, parameters=None):
    config = get_settings("external/wattfox")
    token = authenticate()

    if token is not None:
        response = requests.get(
            config["url"] + url,
            headers={'X-AUTH-TOKEN': token},
            params=parameters
        )
        try:
            print("wattfox success", response.status_code, response.text)
            return response.json()
        except Exception as e:
            print("wattfox error", response.text)
    return None
