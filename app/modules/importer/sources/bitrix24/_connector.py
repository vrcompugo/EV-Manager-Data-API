import requests
import time

from app.modules.settings.settings_services import get_one_item

config = get_one_item("importer/bitrix24")


def authenticate():
    if config is not None and "url" in config["data"]:
        return config["data"]["url"]
    return None


def post(url, post_data=None, files=None):

    base_url = authenticate()

    if base_url is not None:
        response = requests.post(base_url + url, data=post_data)
        try:
            data = response.json()
            if "error" in data and data["error"] == "QUERY_LIMIT_EXCEEDED":
                time.sleep(10)
                return post(url, post_data, files)
            return data
        except Exception as e:
            print(response.text)
    return {}


def get(url, parameters=None):

    base_url = authenticate()

    if base_url is not None:
        response = requests.get(base_url + url,
                            )
        try:
            return response.json()
        except:
            print(response.text)
    return {}
