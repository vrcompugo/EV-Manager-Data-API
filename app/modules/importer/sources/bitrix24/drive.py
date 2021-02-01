import json
import base64
import random
import string


from ._connector import get, post
from app.modules.external.bitrix24.drive import create_folder_path, add_file, add_subfolder


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


def get_file(id):
    data = post("disk.file.get", {
        "id": id
    })
    if "result" in data:
        return data["result"]
    else:
        print("error:", data)
    return None


def get_random_string(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))
