import json
import base64
import random
import string


from ._connector import get, post


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


def get_file(id):
    data = post("disk.file.get", {
        "id": id
    })
    if "result" in data:
        return data["result"]
    else:
        print("error:", data)
    return None


def add_file(data):
    if 'foldername' not in data and 'customer_id' in data:
        data['foldername'] = f"Kunde {data['customer_id']}"
    file_folder_id = create_folder_path(374738, data['foldername'])

    if file_folder_id is None:
        return None

    children = post("disk.folder.getchildren", {
        "id": file_folder_id
    })
    existing_file = None
    for child in children["result"]:
        if child["NAME"] == data["filename"]:
            existing_file = child
    if "file" in data:
        data["file_content"] = data["file"].read()

    if existing_file is None:
        response = post("disk.folder.uploadfile", {
            "id": file_folder_id,
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
        return response["result"]["ID"]
    else:
        print("upload error:", response)
    return None


def get_random_string(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))
