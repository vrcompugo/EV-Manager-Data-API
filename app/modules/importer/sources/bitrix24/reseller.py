import json
import time
from datetime import datetime, timedelta

from app import db
from app.models import Reseller
from app.modules.reseller.services.reseller_services import update_item, add_item
from app.modules.settings.settings_services import get_one_item as get_config_item, update_item as update_config_item

from ._connector import post, get
from ._association import find_association, associate_item
from .customer import run_export as run_customer_export


def filter_import_data(item_data):
    bitrix_department = []
    for department_id in item_data["UF_DEPARTMENT"]:
        department = post("department.get", {"id": department_id})
        time.sleep(0.3)
        if "result" in department and len(department["result"]) > 0:
            bitrix_department.append(department["result"][0]["NAME"])
    group_id = None
    if "efi-Strom (Cloud)" in bitrix_department:
        group_id = 1
    if "Front Sales" in bitrix_department:
        group_id = 1
    if "Vertrieb" in bitrix_department:
        group_id = 1
    if "Mittendrin statt nur dabei" in bitrix_department:
        group_id = 1
    if "Mittendrin statt nur dabei (HV)" in bitrix_department:
        group_id = 6
    if "Südkurve" in bitrix_department:
        group_id = 6
    if "EEG" in bitrix_department:
        group_id = 2
    if "EEG_EEG" in bitrix_department:
        group_id = 2

    if group_id is None:
        return None
    if item_data["EMAIL"] is None or item_data["EMAIL"].strip() == "":
        return None
    data = {
        "group_id": group_id,
        "bitrix_department": ", ".join(bitrix_department),
        "email": item_data["EMAIL"],
        "name": item_data["NAME"] + " " + item_data["LAST_NAME"],
        "phone": item_data["WORK_PHONE"],
        "active": item_data["ACTIVE"]
    }
    return data


def filter_export_data(lead):
    return None


def run_import():
    from app.utils.google_geocoding import geocode_address

    print("Loading Reseller List")
    users_data = {
        "next": 0
    }
    while "next" in users_data:
        users_data = post("user.search", {
            "fields[USER_TYPE]": "employee",
            "start": users_data["next"]
        })
        if "result" in users_data:
            users = users_data["result"]
            for user in users:
                user_data = filter_import_data(user)
                if user_data is not None:
                    print("bitrix reseller import", user_data["email"])
                    link = find_association("Reseller", user["ID"])
                    if link is not None:
                        reseller = Reseller.query.filter(Reseller.id == link.local_id).first()
                    else:
                        reseller = Reseller.query.filter(Reseller.email == user_data["email"]).first()
                    if reseller is not None:
                        reseller = update_item(reseller.id, user_data)
                    else:
                        reseller = add_item(user_data)
                    if link is None and reseller is not None:
                        associate_item("Reseller", remote_id=user["ID"], local_id=reseller.id)


def run_export(remote_id=None, local_id=None):
    pass
