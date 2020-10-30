import requests
import time

from app.modules.settings import get_settings


def authenticate(domain=None):
    config = get_settings(section="external/bitrix24", domain_raw=domain)
    if config is not None and "url" in config:
        return config["url"]
    return None


def post(url, post_data=None, files=None, domain=None):

    base_url = authenticate(domain=domain)

    if base_url is not None:
        response = requests.post(base_url + url, data=post_data)
        try:
            data = response.json()
            if "error" in data and data["error"] == "QUERY_LIMIT_EXCEEDED":
                time.sleep(10)
                return post(url, post_data, files)
            return data
        except Exception as e:
            print("error", response.text)
    return {}


def get(url, parameters=None):

    base_url = authenticate()

    if base_url is not None:
        response = requests.get(base_url + url, params=parameters)
        try:
            data = response.json()
            if "error" in data and data["error"] == "QUERY_LIMIT_EXCEEDED":
                time.sleep(10)
                return get(url, parameters)
            return data
        except Exception as e:
            print(response.text)
    return {}
