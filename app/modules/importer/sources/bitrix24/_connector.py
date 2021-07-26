import requests
import time
import json
import traceback
import sys

from app.modules.settings.settings_services import get_one_item

config = get_one_item("importer/bitrix24")


def authenticate():
    if config is not None and "url" in config["data"]:
        return config["data"]["url"]
    return None


def post(url, post_data=None, files=None):

    base_url = authenticate()

    if base_url is not None:
        if url == "disk.folder.getchildren":
            print("disk.folder.getchildren", post_data)
        response = requests.post(base_url + url, data=post_data)
        try:
            data = response.json()
            if "error" in data and data["error"] == "QUERY_LIMIT_EXCEEDED":
                time.sleep(5)
                if post_data.get("fileContent[1]") is not None:
                    print(url, "with filecontent")
                else:
                    print(url, json.dumps(post_data, indent=2))
                traceback.print_exc(file=sys.stdout)
                print("query limit reached")
                return post(url, post_data, files)
            return data
        except Exception as e:
            print(e)
            print("error1", response.text)
    return {}


def get(url, parameters=None):

    base_url = authenticate()

    if base_url is not None:
        response = requests.get(base_url + url, params=parameters)
        try:
            data = response.json()
            if "error" in data and data["error"] == "QUERY_LIMIT_EXCEEDED":
                time.sleep(5)
                return get(url, parameters)
            return data
        except Exception as e:
            print(response.text)
    return {}
