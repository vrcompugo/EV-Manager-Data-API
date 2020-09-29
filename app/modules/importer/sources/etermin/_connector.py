import requests
import base64
import random
import hmac
import hashlib
import re

from app.modules.settings.settings_services import get_one_item

config = get_one_item("importer/etermin")


def authenticate():
    if config is None:
        print("no config for etermin")
        return None
    token = {
        "publickey": config["data"]["public_key"],
        "salt": str(random.getrandbits(32))
    }
    signature = hmac.new(config["data"]["private_key"].encode("utf-8"), msg=token["salt"].encode("utf-8"), digestmod=hashlib.sha256).digest()

    token["signature"] = base64.encodebytes(signature).decode("utf-8").replace("\n", "")
    return token


def get(url, parameters=None):

    token = authenticate()

    if token is not None:
        token["Accept"] = "application/json"
        response = requests.get(
            config["data"]["url"] + url,
            headers=token,
            params=parameters
        )
        try:
            return response.json()
        except Exception as e:
            print(response.text)
    return None


def post(url, post_data=None, files=None):

    token = authenticate()

    if token is not None:
        token["Accept"] = "application/json"
        response = requests.post(
            config["data"]["url"] + url,
            headers=token,
            data=post_data
        )
        try:
            xml_id = re.findall(r'\<id\>([0-9]*)\<\/id\>', response.text)
            if len(xml_id) > 0:
                return {"cid": int(xml_id[0])}
            data = response.json()
            return data
        except Exception as e:
            print(response.text)
    return None


def put(url, post_data=None, files=None):

    token = authenticate()

    if token is not None:
        token["Accept"] = "application/json"
        response = requests.put(
            config["data"]["url"] + url,
            headers=token,
            data=post_data
        )
        try:
            xml_id = re.findall(r'\<id\>([0-9]*)\<\/id\>', response.text)
            if len(xml_id) > 0:
                if xml_id[0] == "":
                    return {"status": "success"}
                return {"cid": int(xml_id[0])}
            data = response.json()
            return data
        except Exception as e:
            print(response.text)
    return None
