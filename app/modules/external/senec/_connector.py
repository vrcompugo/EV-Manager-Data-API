import requests
import base64

from app.modules.settings import get_settings


def authenticate():
    config = get_settings("external/senec")
    if config is None:
        print("no config for senec")
        return None
    response = requests.post(
        config["url"] + "/auth",
        data={
            "username": config["username"],
            "password": config["password"]
        }
    )

    if response.status_code == 200:
        data = response.json()
        if "token" in data:
            return data["token"]
    return None


def get(url, parameters=None):

    config = get_settings("external/senec")
    token = authenticate()

    if token is not None:
        response = requests.get(
            config["url"] + url,
            headers={'Authorization': "Bearer {}".format(token)},
            params=parameters
        )
        try:
            data = response.json()
            print("resp?", data)
            if "assignments" in data:
                return data["assignments"]
            return None
        except Exception as e:
            print(response.text)
    return None
