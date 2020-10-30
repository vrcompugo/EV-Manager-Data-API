import json
import base64
import random
import requests
import string

from app.modules.auth import get_auth_info
from app.modules.settings import get_settings
from app.modules.auth.jwt_parser import encode_jwt

from ._connector import get, post


def get_file(id):
    data = post("disk.file.get", {
        "id": id
    })
    if "result" in data:
        return data["result"]
    else:
        print("error:", data)
    return None


def get_file_content(id):
    file_data = get_file(id)
    if file_data is None:
        print("error: cant get file for content")
    result = requests.get(file_data["DOWNLOAD_URL"])
    return result.content


def get_attached_file(id):
    data = post("disk.file.get", {
        "id": 16190
    })
    if "result" in data:
        return data["result"]
    else:
        print("error:", data)
    return None


def get_folder(id):
    payload = {
        "id": id,
        "start": 0
    }
    result = []
    while payload["start"] is not None:
        data = post("disk.folder.getchildren", payload)
        if "result" in data:
            payload["start"] = data["next"] if "next" in data else None
            result = result + data["result"]
        else:
            print("error:", data)
            payload["start"] = None
            return None
    return result


def create_folder_path(parent_folder_id, path):
    parts = path.split("/")
    children = get_folder(parent_folder_id)
    for part in parts:
        if children is None:
            existing_child = None
        else:
            existing_child = next((item for item in children if item["NAME"] == str(part)), None)
        if existing_child is not None:
            parent_folder_id = existing_child["ID"]
            children = get_folder(existing_child["ID"])
        else:
            result = add_subfolder(parent_folder_id, part)
            if result is not None and "ID" in result and result["ID"] > 0:
                parent_folder_id = int(result["ID"])
                children = get_folder(parent_folder_id)
            else:
                break
    return parent_folder_id


def add_subfolder(parent_id, subfolder_name):
    data = post("disk.folder.addsubfolder", {
        "id": parent_id,
        "data[NAME]": subfolder_name
    })
    if "result" in data:
        return data["result"]
    else:
        print("error:", data)
    return None


def add_file(folder_id, data):
    config = get_settings(section="external/bitrix24")
    folders = {"next": 0, "total": 1}

    children = post("disk.folder.getchildren", {
        "id": folder_id
    })
    existing_file = None
    for child in children["result"]:
        if child["NAME"] == data["filename"]:
            existing_file = child
    if "file" in data:
        data["file_content"] = data["file"].read()

    if existing_file is None:
        response = post("disk.folder.uploadfile", {
            "id": folder_id,
            "data[NAME]": data["filename"],
            "fileContent[0]": data["filename"],
            "fileContent[1]": base64.encodestring(data["file_content"]).decode("utf-8")
        })
    else:
        response = post("disk.file.uploadversion", {
            "id": existing_file["ID"],
            "fileContent[0]": data["filename"],
            "fileContent[1]": base64.encodestring(data["file_content"]).decode("utf-8")
        })
    if "result" in response:
        return int(response["result"]["ID"])
    else:
        print(response)
    return None


def get_public_link(id, expire_minutes=86400):
    auth_info = get_auth_info()
    config = get_settings(section="general")
    if auth_info is not None and auth_info["domain_raw"] is not None:
        token_data = encode_jwt({"file_id": id, "domain": auth_info["domain_raw"]}, expire_minutes)
        return f"{config['base_url']}files/view/{token_data['token']}"
    return None


def get_random_string(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))
