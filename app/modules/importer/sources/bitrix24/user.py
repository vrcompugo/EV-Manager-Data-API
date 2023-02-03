import json
import time
import random
import string

from app import db
from app.models import User
from app.modules.external.bitrix24.department import get_department
from app.modules.user.user_services import add_item, update_item

from ._connector import post, get
from ._association import find_association, associate_item


def filter_import_data(item_data):
    bitrix_department = []
    for department_id in item_data["UF_DEPARTMENT"]:
        department = get_department(department_id)
        if department is not None:
            bitrix_department.append(department["NAME"])
    role_id = 3
    if "Innendienst" in bitrix_department:
        role_id = 5
    if "Front Sales" in bitrix_department:
        role_id = 5
    if "After Sales" in bitrix_department:
        role_id = 5
    if "Montage" in bitrix_department:
        role_id = 10
    if "Montage II (Dach&PV)" in bitrix_department:
        role_id = 10
    if "Montage III (PV)" in bitrix_department:
        role_id = 10
    if "Montage Team III" in bitrix_department:
        role_id = 10
    if "Team Hybrid EnPal" in bitrix_department:
        role_id = 10
    if "Technik & Service" in bitrix_department:
        role_id = 12
    if "Service & Wartung" in bitrix_department:
        role_id = 14
    if "Elektrik Abteilung" in bitrix_department:
        role_id = 14
    if "Einkauf, Logistik, Fuhrpark" in bitrix_department:
        role_id = 11
    if "Wärme & Wasser (KEZ)" in bitrix_department:
        role_id = 10

    if item_data["EMAIL"] is None or item_data["EMAIL"].strip() == "":
        return None
    data = {
        "roles": [],
        "bitrix_department": ", ".join(bitrix_department),
        "email": item_data["EMAIL"],
        "username": item_data["EMAIL"],
        "name": str(item_data.get("NAME")) + " " + str(item_data.get("LAST_NAME")),
        "active": item_data["ACTIVE"]
    }
    if role_id is not None:
        data["roles"] = [role_id]
    return data


def filter_export_data(lead):
    return None


def run_import():

    print("Loading User List")
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
                    print("bitrix user import", user_data["email"])
                    link = find_association("User", user["ID"])
                    if link is not None:
                        user_model = User.query.filter(User.id == link.local_id).first()
                    else:
                        user_model = User.query.filter(User.email == user_data["email"]).first()
                    if user_model is not None:
                        user_model = update_item(user_model.id, user_data)
                    else:
                        user_data["password"] = ''.join(random.choice(string.ascii_lowercase) for i in range(24))
                        user_model = add_item(user_data)
                    if link is None and user_model is not None:
                        associate_item("User", remote_id=user["ID"], local_id=user_model.id)


def run_cron_import():
    return run_import()


def run_export(remote_id=None, local_id=None):
    pass
