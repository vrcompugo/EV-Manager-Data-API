import json
import time
import os
import base64
import random
import requests
import string

from app import db
from app.modules.auth import get_auth_info
from app.modules.settings import get_settings
from app.modules.auth.jwt_parser import encode_jwt

from ._connector import get, post
from .models.drive_folder import BitrixDriveFolder

FOLDER_CACHE = {}


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
    if result.content[:1] == b'{' or result.content[:1] == b'[':
        try:
            print("file content: error", result.content[:1])
            data = result.json()
            if "error" in data and data["error"] == "QUERY_LIMIT_EXCEEDED":
                time.sleep(10)
                print("FILE CONtent QUERY_LIMIT_EXCEEDED")
                # return get_file_content(id)
        except Exception as e:
            pass
    return result.content


def get_file_content_cached(id):
    if os.path.exists(f"/tmp/bitrix-filecache-{id}"):
        with open(f"/tmp/bitrix-filecache-{id}", "rb") as fh:
            content = fh.read()
        return content
    content = get_file_content(id)
    with open(f"/tmp/bitrix-filecache-{id}", "wb") as fh:
        fh.write(content)
    return content


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
            print("error3:", data)
            payload["start"] = None
            return None
    return result


def get_folder_id(parent_folder_id, subfolder):
    subfolder = subfolder.strip("/")
    folder = BitrixDriveFolder.query\
        .filter(BitrixDriveFolder.parent_folder_id == parent_folder_id)\
        .filter(BitrixDriveFolder.path == subfolder)\
        .first()
    if folder is not None:
        return folder.bitrix_id
    children = get_folder(parent_folder_id)
    existing_child = next((item for item in children if item["NAME"] == str(subfolder)), None)
    if existing_child is not None:
        folder = BitrixDriveFolder(
            bitrix_id=existing_child["ID"],
            parent_folder_id=parent_folder_id,
            path=subfolder
        )
        db.session.add(folder)
        db.session.commit()
        return existing_child["ID"]
    else:
        return None


def create_folder_path(parent_folder_id, path):
    path = path.strip("/")
    parts = path.split("/")
    new_path = ""
    for part in parts:
        new_folder_id = get_folder_id(parent_folder_id, part)
        if new_folder_id is None:
            new_folder = add_subfolder(parent_folder_id, part)
            new_folder_id = new_folder["ID"]
            folder = BitrixDriveFolder(
                bitrix_id=new_folder_id,
                parent_folder_id=parent_folder_id,
                path=part
            )
            db.session.add(folder)
            db.session.commit()
        parent_folder_id = new_folder_id
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

    response = post("disk.folder.uploadfile", {
        "id": folder_id,
        "data[NAME]": data["filename"],
        "fileContent[0]": data["filename"],
        "fileContent[1]": base64.encodestring(data["file_content"]).decode("utf-8")
    })
    if "result" not in response:
        print("add_file error", response)
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
    config = get_settings(section="general")
    token_data = encode_jwt({"file_id": id}, expire_minutes)
    return f"{config['base_url']}files/view/{token_data['token']}"


def get_random_string(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))
