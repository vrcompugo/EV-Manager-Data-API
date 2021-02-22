import json
import time
import os
import base64
import random
import requests
import string
from datetime import datetime

from app import db
from app.modules.auth import get_auth_info
from app.modules.settings import get_settings, set_settings
from app.modules.auth.jwt_parser import encode_jwt

from ._connector import get, post
from .models.drive_folder import BitrixDriveFolder
from .contact import get_contacts, get_contact, update_contact
from .deal import get_deal, get_deals, update_deal

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
                time.sleep(5)
                print("FILE CONtent QUERY_LIMIT_EXCEEDED")
                return get_file_content(id)
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


def get_folder(id, namefilter=None):
    payload = {
        "id": id,
        "start": 0
    }
    if namefilter is not None:
        payload["filter[NAME]"] = namefilter
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
    children = get_folder(parent_folder_id, subfolder)
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
        if data["error"] == "DISK_OBJ_22000":
            print({
                "id": parent_id,
                "data[NAME]": subfolder_name
            })
            return {"ID": get_folder_id(parent_id, subfolder_name)}
        print("error new folder:", data)
    return None


def add_file(folder_id, data):

    if data.get("bitrix_file_id", None) is not None:
        response = post("disk.file.uploadversion", {
            "id": data.get("bitrix_file_id"),
            "fileContent[0]": data["filename"],
            "fileContent[1]": base64.encodestring(data["file_content"]).decode("utf-8")
        })
    else:
        existing_file = None
        children = get_folder(folder_id, data["filename"])
        for child in children:
            if child["NAME"] == data["filename"]:
                existing_file = child
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
        if "result" not in response:
            print("add_file error", response)
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


def run_cron_folder_creation():
    config = get_settings("external/bitrix24/folder_creation")
    print("folder_creation")
    if config is None or "folders" not in config:
        print("no config for folder_creation")
        return None
    last_import = datetime(2021, 2, 6, 0, 0, 0)
    import_time = datetime.now()
    if "last_run_time" in config:
        last_import = datetime.strptime(config["last_run_time"], "%Y-%m-%d %H:%M:%S.%f")

    contacts = get_contacts({
        "ORDER[DATE_CREATE]": "DESC",
        "FILTER[>DATE_CREATE]": str(last_import),
        "SELECT[0]": "ID",
        "SELECT[1]": "UF_CRM_1612518385676",
        "SELECT[2]": "UF_CRM_1612533349639",
        "SELECT[3]": "UF_CRM_1612533369175",
        "SELECT[4]": "UF_CRM_1612533388171",
        "SELECT[5]": "UF_CRM_1612533409927",
        "SELECT[6]": "UF_CRM_1612533423669",
        "SELECT[7]": "UF_CRM_1612533445604",
        "SELECT[8]": "UF_CRM_1612533596622",
        "SELECT[9]": "UF_CRM_1612533461553",
        "SELECT[10]": "UF_CRM_1612533480143",
        "SELECT[11]": "UF_CRM_1612533500465"
    })

    for contact in contacts:
        post_data = {}
        for folder in config["folders"]:
            time.sleep(1)
            if contact.get(folder["key"]) in [None, "", "0", 0]:
                subpath = f"Kunde {contact['id']}"
                new_folder_id = create_folder_path(folder["folder_id"], subpath)
                if new_folder_id is not None:
                    if folder["key"] == "drive_myportal_folder":
                        create_folder_path(new_folder_id, "Documents")
                        create_folder_path(new_folder_id, "Data Sheets")
                        create_folder_path(new_folder_id, "Protocols")
                        create_folder_path(new_folder_id, "Various")
                    post_data[folder["key"]] = f"{folder['base_url']}{subpath}"
        if len(post_data) > 0:
            update_contact(contact["id"], post_data)

    drive_insurance_folder = next((item for item in config["folders"] if item["key"] == "drive_insurance_folder"), None)
    if drive_insurance_folder is not None:
        deals_insurance = get_deals({"FILTER[CATEGORY_ID]": "70", "FILTER[>DATE_CREATE]": str(last_import)})
        for deal in deals_insurance:
            deal = get_deal(deal["id"])
            if deal.get("drive_insurance_folder") in [None, "", "0", 0]:
                deal_path = get_deal_path(deal, "")
                create_folder_path(drive_insurance_folder["folder_id"], deal_path)
                update_deal(deal["id"], {"drive_insurance_folder": f"{drive_insurance_folder['base_url']}{deal_path}"})
                time.sleep(1)
        deals_insurance_external = get_deals({"FILTER[CATEGORY_ID]": "110", "FILTER[>DATE_CREATE]": str(last_import)})
        for deal in deals_insurance_external:
            deal = get_deal(deal["id"])
            if deal.get("drive_insurance_folder") in [None, "", "0", 0]:
                deal_path = get_deal_path(deal, "")
                create_folder_path(drive_insurance_folder["folder_id"], deal_path)
                update_deal(deal["id"], {"drive_insurance_folder": f"{drive_insurance_folder['base_url']}{deal_path}"})
                time.sleep(1)

    drive_rental_folder = next((item for item in config["folders"] if item["key"] == "drive_rental_contract_folder"), None)
    drive_rental_folder2 = next((item for item in config["folders"] if item["key"] == "drive_rental_documents_folder"), None)
    if drive_rental_folder is not None and drive_rental_folder2 is not None:
        deals_rental = get_deals({"FILTER[CATEGORY_ID]": "168", "FILTER[>DATE_CREATE]": str(last_import)})
        for deal in deals_rental:
            deal = get_deal(deal["id"])
            if deal.get("drive_rental_contract_folder") in [None, "", "0", 0]:
                deal_path = get_deal_path(deal, "")
                create_folder_path(drive_rental_folder["folder_id"], deal_path)
                update_deal(deal["id"], {"drive_rental_contract_folder": f"{drive_rental_folder['base_url']}{deal_path}"})
                create_folder_path(drive_rental_folder2["folder_id"], deal_path)
                update_deal(deal["id"], {"drive_rental_documents_folder": f"{drive_rental_folder2['base_url']}{deal_path}"})
                time.sleep(1)

    drive_cloud_folder = next((item for item in config["folders"] if item["key"] == "drive_cloud_folder"), None)
    if drive_cloud_folder is not None:
        deals_cloud = get_deals({"FILTER[CATEGORY_ID]": "15", "FILTER[>DATE_CREATE]": str(last_import)})
        for deal in deals_cloud:
            deal = get_deal(deal["id"])
            if deal.get("drive_cloud_folder") in [None, "", "0", 0]:
                deal_path = get_deal_path(deal, "")
                create_folder_path(drive_cloud_folder["folder_id"], deal_path)
                update_deal(deal["id"], {"drive_cloud_folder": f"{drive_cloud_folder['base_url']}{deal_path}"})
                time.sleep(1)

    config = get_settings("external/bitrix24/folder_creation")
    if config is not None:
        config["last_run_time"] = str(import_time)
    set_settings("external/bitrix24/folder_creation", config)


def get_deal_path(deal, path):
    path = path.strip("/")
    new_path = ""
    if deal.get("contact_id") not in [None, "", "0", 0]:
        new_path = f"Kunde {deal['contact_id']}/"
    if deal.get("unique_identifier") in [None, "", "0", 0]:
        return f"{new_path}Auftrag {deal['id']}/{path}"
    return f"{new_path}Vorgang {deal['unique_identifier']}/{path}"


def run_legacy_folder_creation():
    from .contact import convert_config_values
    config = get_settings("external/bitrix24/folder_creation")
    print("folder_creation")
    if config is None or "folders" not in config:
        print("no config for folder_creation")
        return None

    payload = {
        "ORDER[DATE_CREATE]": "DESC",
        "SELECT[0]": "ID",
        "SELECT[1]": "UF_CRM_1612518385676",
        "SELECT[2]": "UF_CRM_1612533349639",
        "SELECT[3]": "UF_CRM_1612533369175",
        "SELECT[4]": "UF_CRM_1612533388171",
        "SELECT[5]": "UF_CRM_1612533409927",
        "SELECT[6]": "UF_CRM_1612533423669",
        "SELECT[7]": "UF_CRM_1612533445604",
        "SELECT[8]": "UF_CRM_1612533596622",
        "SELECT[9]": "UF_CRM_1612533461553",
        "SELECT[10]": "UF_CRM_1612533480143",
        "SELECT[11]": "UF_CRM_1612533500465"
    }
    payload["start"] = 0
    while payload["start"] is not None:
        data = post("crm.contact.list", payload)
        if "result" in data:
            payload["start"] = data["next"] if "next" in data else None
            print("batch", payload["start"])
            for item in data["result"]:
                contact = convert_config_values(item)
                post_data = {}
                for folder in config["folders"]:
                    if contact.get(folder["key"]) in [None, "", "0", 0]:
                        print(f"Kunde {contact['id']}")
                        time.sleep(10)
                        print(f"Kunde {contact['id']}")
                        subpath = f"Kunde {contact['id']}"
                        new_folder_id = create_folder_path(folder["folder_id"], subpath)
                        if new_folder_id is not None:
                            if folder["key"] == "drive_myportal_folder":
                                create_folder_path(new_folder_id, "Documents")
                                time.sleep(1)
                                create_folder_path(new_folder_id, "Data Sheets")
                                time.sleep(1)
                                create_folder_path(new_folder_id, "Protocols")
                                time.sleep(1)
                                create_folder_path(new_folder_id, "Various")
                                time.sleep(1)
                            post_data[folder["key"]] = f"{folder['base_url']}{subpath}"
                if len(post_data) > 0:
                    update_contact(contact["id"], post_data)
                    print("update", contact["id"])
