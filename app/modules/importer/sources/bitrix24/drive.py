import json
import base64
import random
import string


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


def add_file(data):
    folders = post("disk.folder.getchildren", {
        "id": 374738
    })
    file_folder_id = None
    for folder in folders["result"]:
        if 'customer_id' in data and folder["NAME"] == f"Kunde {data['customer_id']}":
            file_folder_id = folder["ID"]
            break
        if 'foldername' in data and folder["NAME"] == data["foldername"]:
            file_folder_id = folder["ID"]
            break

    if file_folder_id is None:
        if 'foldername' not in data and 'customer_id' in data:
            data['foldername'] = f"Kunde {data['customer_id']}"
        response = post("disk.folder.addsubfolder", {
            "id": 374738,
            "data[NAME]": data['foldername']
        })
        if "result" in response:
            file_folder_id = response["result"]["ID"]

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
    return None


def get_random_string(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))
