import requests
import time
import json
import traceback
import sys

from app.modules.settings import get_settings


def authenticate(domain=None):
    config = get_settings(section="external/bitrix24", domain_raw=domain)
    if config is not None and "url" in config:
        return config["url"]
    return None


def post(url, post_data=None, files=None, domain=None, no_repeat=False):

    base_url = authenticate(domain=domain)

    if base_url is not None:
        response = requests.post(base_url + url, data=post_data)
        try:
            data = response.json()
            if "error" in data and data["error"] == "QUERY_LIMIT_EXCEEDED":
                time.sleep(2)
                # if post_data.get("fileContent[1]") is not None:
                #     print(url, "with filecontent")
                # else:
                #     print(url, json.dumps(post_data, indent=2))
                traceback.print_exc(file=sys.stdout)
                print("query limit reached")
                return post(url, post_data, files, domain)
            return data
        except Exception as e:
            print(e)
            print("error1", response.text)
    if no_repeat is False:
        return post(url, post_data=post_data, files=files, domain=domain, no_repeat=True)
    return {}


def get(url, parameters=None):

    base_url = authenticate()

    if base_url is not None:
        response = requests.get(base_url + url, params=parameters)
        try:
            data = response.json()
            if "error" in data and data["error"] == "QUERY_LIMIT_EXCEEDED":
                time.sleep(2)
                print("query limit reached")
                return get(url, parameters)
            return data
        except Exception as e:
            print(response.text)
    return {}
