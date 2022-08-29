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
        print("error get file:", data)
    return None


def get_file_content(id):
    file_data = get_file(id)
    if file_data is None:
        print("error: cant get file for content")
    result = requests.get(file_data["DOWNLOAD_URL"])
    if result.content[:1] == b'{' or result.content[:1] == b'[':
        try:
            print("file content: error", id, result.content[:100])
            data = result.json()
            if "error" in data and data["error"] in ["QUERY_LIMIT_EXCEEDED", "OPERATION_TIME_LIMIT", "INTERNAL_SERVER_ERROR"]:
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
            print(payload)
            payload["start"] = None
            return None
    return result


def get_folder_id(parent_folder_id, subfolder=None, path=None):
    if subfolder is not None:
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
        return None
    if path is not None:
        path = path.strip("/")
        parts = path.split("/")
        for part in parts:
            new_folder_id = get_folder_id(parent_folder_id, part)
            if new_folder_id is None:
                return None
            parent_folder_id = new_folder_id
        return parent_folder_id


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
        print("error new folder3:", data)
        return data["result"]
    else:
        if data["error"] == "DISK_OBJ_22000":
            print("error new folder2:", data)
            return {"ID": get_folder_id(parent_id, subfolder_name)}
        print("error new folder:", data)
    return None


def rename_folder(folder_id, new_name):
    data = post("disk.folder.rename", {
        "id": folder_id,
        "newName": new_name
    })
    if "result" in data:
        return data["result"]
    else:
        print("error rename folder:", data)
    return None


def add_file(folder_id, data):

    '''children = get_folder(folder_id, data["filename"])
    existing_file = None
    for child in children:
        if child["NAME"] == data["filename"]:
            existing_file = child'''
    if "file" in data:
        data["file_content"] = data["file"].read()

    response = post("disk.folder.uploadfile", {
        "id": folder_id,
        "data[NAME]": data["filename"],
        "fileContent[0]": data["filename"],
        "fileContent[1]": base64.encodestring(data["file_content"]).decode("utf-8")
    })
    if response.get("error") == "DISK_OBJ_22000":
        children = get_folder(folder_id, data["filename"])
        existing_file = None
        for child in children:
            if child["NAME"] == data["filename"]:
                existing_file = child
        if existing_file is not None:
            response = post("disk.file.uploadversion", {
                "id": existing_file["ID"],
                "fileContent[0]": data["filename"],
                "fileContent[1]": base64.encodestring(data["file_content"]).decode("utf-8")
            })
        else:
            data["filename"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S") + data["filename"]
            response = post("disk.folder.uploadfile", {
                "id": folder_id,
                "data[NAME]": data["filename"],
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


def run_cron_folder_creation():
    config = get_settings("external/bitrix24/folder_creation")
    print("folder_creation")
    if config is None or "folders" not in config:
        print("no config for folder_creation")
        return None
    last_import = "2021-02-06"
    import_time = datetime.now()
    if "last_run_time" in config:
        last_import = config["last_run_time"]

    contacts = get_contacts({
        "ORDER[DATE_CREATE]": "DESC",
        "FILTER[>DATE_MODIFY]": last_import,
        "SELECT": "full"
    }, force_reload=True)
    if contacts is None:
        print("contacts could not be loaded")
        return
    for contact in contacts:
        post_data = {}
        for folder in config["folders"]:
            subpath = f"Kunde {contact['id']}"
            base_url = folder['base_url'].strip("/")
            if contact.get(folder["key"]) != f"{base_url}/{subpath}":
                print("folderlink", contact.get(folder["key"]), f"{base_url}/{subpath}")
                new_folder_id = create_folder_path(folder["folder_id"], subpath)
                if new_folder_id is not None:
                    if folder["key"] == "drive_myportal_folder":
                        create_folder_path(new_folder_id, "Vertragsunterlagen")
                        create_folder_path(new_folder_id, "Datenblätter")
                        create_folder_path(new_folder_id, "Protokolle")
                        create_folder_path(new_folder_id, "Verschiedenes")
                    post_data[folder["key"]] = f"{base_url}/{subpath}"
        if len(post_data) > 0:
            print("update contact:", contact["id"])
            update_contact(contact["id"], post_data)

    drive_insurance_folder = next((item for item in config["folders"] if item["key"] == "drive_insurance_folder"), None)
    if drive_insurance_folder is not None:
        deals_insurance = get_deals({"FILTER[CATEGORY_ID]": "70", "FILTER[>DATE_CREATE]": str(last_import)}, force_reload=True)
        for deal in deals_insurance:
            print("deal:", deal["id"])
            deal = get_deal(deal["id"])
            if deal.get("drive_insurance_folder") in [None, "", "0", 0]:
                deal_path = get_deal_path(deal, "")
                create_folder_path(drive_insurance_folder["folder_id"], deal_path)
                update_deal(deal["id"], {"drive_insurance_folder": f"{drive_insurance_folder['base_url']}{deal_path}"})
                time.sleep(1)
        deals_insurance_external = get_deals({"FILTER[CATEGORY_ID]": "110", "FILTER[>DATE_CREATE]": str(last_import)}, force_reload=True)
        for deal in deals_insurance_external:
            print("deal:", deal["id"])
            deal = get_deal(deal["id"])
            if deal.get("drive_insurance_folder") in [None, "", "0", 0]:
                deal_path = get_deal_path(deal, "")
                create_folder_path(drive_insurance_folder["folder_id"], deal_path)
                update_deal(deal["id"], {"drive_insurance_folder": f"{drive_insurance_folder['base_url']}{deal_path}"})
                time.sleep(1)

    drive_rental_folder = next((item for item in config["folders"] if item["key"] == "drive_rental_contract_folder"), None)
    drive_rental_folder2 = next((item for item in config["folders"] if item["key"] == "drive_rental_documents_folder"), None)
    if drive_rental_folder is not None and drive_rental_folder2 is not None:
        deals_rental = get_deals({"FILTER[CATEGORY_ID]": "168", "FILTER[>DATE_CREATE]": str(last_import)}, force_reload=True)
        for deal in deals_rental:
            print("deal:", deal["id"])
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
        deals_cloud = get_deals({"FILTER[CATEGORY_ID]": "15", "FILTER[>DATE_CREATE]": str(last_import)}, force_reload=True)
        for deal in deals_cloud:
            print("deal:", deal["id"])
            deal = get_deal(deal["id"])
            if deal.get("drive_cloud_folder") in [None, "", "0", 0]:
                deal_path = get_deal_path(deal, "")
                create_folder_path(drive_cloud_folder["folder_id"], deal_path)
                update_deal(deal["id"], {"drive_cloud_folder": f"{drive_cloud_folder['base_url']}{deal_path}"})
                time.sleep(1)

    config = get_settings("external/bitrix24/folder_creation")
    if config is not None:
        config["last_run_time"] = import_time.astimezone().isoformat()
    set_settings("external/bitrix24/folder_creation", config)


def get_deal_path(deal, path):
    path = path.strip("/")
    new_path = ""
    if deal.get("contact_id") not in [None, "", "0", 0]:
        new_path = f"Kunde {deal['contact_id']}/"
    if deal.get("unique_identifier") in [None, "", "0", 0]:
        return f"{new_path}Auftrag {deal['id']}/{path}"
    return f"{new_path}Vorgang {deal['unique_identifier']}/{path}"


def run_cron_heating_folder_creation():
    config = get_settings("external/bitrix24/folder_creation")
    print("heating_folder_creation")
    if config is None or "folders" not in config:
        print("no config for heating_folder_creation")
        return None
    last_import = "2021-01-01"
    import_time = datetime.now()
    if "last_heating_run_time" in config:
        last_import = config["last_heating_run_time"]

    deals = get_deals({
        "FILTER[>DATE_MODIFY]": last_import,
        "FILTER[CATEGORY_ID]": 9,
        "SELECT[0]": "*",
        "SELECT[1]": "ID",
        "SELECT[2]": "UF_CRM_60A60FF556B0C"
    }, force_reload=True)
    if deals is None:
        print("deals could not be loaded")
        return
    for deal in deals:
        print("deal", deal["id"])
        if deal.get("upload_link_heatingcontract") in [None, "", 0]:
            deal_path = f"Auftrag {deal['id']}"
            folder_id = create_folder_path(1321602, deal_path)
            update_deal(deal["id"], {
                "folder_id_heatingcontract": folder_id,
                "upload_link_heatingcontract": f"https://keso.bitrix24.de/docs/path/Heizungsupload/{deal_path}"
            })
    config = get_settings("external/bitrix24/folder_creation")
    if config is not None:
        config["last_heating_run_time"] = import_time.astimezone().isoformat()
    set_settings("external/bitrix24/folder_creation", config)


def run_cron_external_company_folder_creation():
    config = get_settings("external/bitrix24/folder_creation")
    print("external_company_folder_creation")
    if config is None or "folders" not in config:
        print("no config for external_company_folder_creation")
        return None
    last_import = "2021-01-01"
    import_time = datetime.now()
    if "last_external_company_run_time" in config:
        last_import = config["last_external_company_run_time"]

    deals = get_deals({
        "FILTER[>DATE_MODIFY]": last_import,
        "FILTER[CATEGORY_ID]": 142,
        "SELECT": "full"
    }, force_reload=True)
    if deals is None:
        print("deals could not be loaded")
        return
    for deal in deals:
        print("deal", deal["id"])
        if deal.get("upload_link_roof") in [None, "", 0]:
            deal_path = f"Extern {deal['id']}"
            link_path = f"https://keso.bitrix24.de/docs/path/Auftragsordner/{deal_path}"
            data = {}
            data["upload_folder_id_roof"] = create_folder_path(parent_folder_id=442678, path=f"{deal_path}/Uploads/Dachbilder")
            data["upload_link_roof"] = f"{link_path}/Uploads/Dachbilder"
            data["upload_folder_id_roof_extra"] = create_folder_path(parent_folder_id=442678, path=f"{deal_path}/Uploads/Weitere Dachbilder")
            data["upload_link_roof_extra"] = f"{link_path}/Uploads/Weitere Dachbilder"
            data["upload_folder_id_electric"] = create_folder_path(parent_folder_id=442678, path=f"{deal_path}/Uploads/Elektrik-Bilder")
            data["upload_link_electric"] = f"{link_path}/Uploads/Elektrik-Bilder"
            data["upload_folder_id_heating"] = create_folder_path(parent_folder_id=442678, path=f"{deal_path}/Uploads/Heizungsbilder")
            data["upload_link_heating"] = f"{link_path}/Uploads/Heizungsbilder"
            data["upload_folder_id_invoices"] = create_folder_path(parent_folder_id=442678, path=f"{deal_path}/Uploads/Rechnung vom bisherigem Anbieter")
            data["upload_link_invoices"] = f"{link_path}/Uploads/Rechnung vom bisherigem Anbieter"
            data["upload_folder_id_contract"] = create_folder_path(parent_folder_id=442678, path=f"{deal_path}/Uploads/Vertragsunterlagen")
            data["upload_link_contract"] = f"{link_path}/Uploads/Vertragsunterlagen"

            update_data = {
                "upload_link_roof": data["upload_link_roof"],
                "upload_link_electric": data["upload_link_electric"],
                "upload_link_heating": data["upload_link_heating"],
                "upload_link_invoices": data["upload_link_invoices"],
                "upload_link_contract": data["upload_link_contract"]
            }
            update_deal(deal["id"], update_data)
    config = get_settings("external/bitrix24/folder_creation")
    if config is not None:
        config["last_external_company_run_time"] = import_time.astimezone().isoformat()
    set_settings("external/bitrix24/folder_creation", config)


def run_legacy_folder_creation():
    payload = {
        "id": 649168,
        "start": 0
    }
    while payload["start"] is not None:
        data = post("disk.folder.getchildren", payload, force_reload=True)
        if "result" in data:
            payload["start"] = data["next"] if "next" in data else None
            for folder in data["result"]:
                print(folder["NAME"])
                subfolders = get_folder(folder["ID"])
                for subfolder in subfolders:
                    if subfolder["NAME"] == "Documents":
                        rename_folder(subfolder["ID"], "Vertragsunterlagen")
                        time.sleep(4)
                    if subfolder["NAME"] == "Data Sheets":
                        rename_folder(subfolder["ID"], "Datenblätter")
                        time.sleep(4)
                    if subfolder["NAME"] == "Protocols":
                        rename_folder(subfolder["ID"], "Protokolle")
                        time.sleep(4)
                    if subfolder["NAME"] == "Various":
                        rename_folder(subfolder["ID"], "Verschiedenes")
                        time.sleep(4)
        else:
            print("error3:", data)
            payload["start"] = None
            return None
