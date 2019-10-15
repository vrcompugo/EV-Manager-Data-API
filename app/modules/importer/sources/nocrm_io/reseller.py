from app import db
import pprint

from app.modules.reseller.services.reseller_services import add_item , update_item
from app.modules.reseller.services.reseller_group_services import add_item as group_add_item, update_item as group_update_item
from app.modules.reseller.models.reseller import Reseller
from app.modules.reseller.models.reseller_group import ResellerGroup


from ._connector import post, get
from ._association import find_association, associate_item


def filter_input(remote_data):

    data = None

    group = find_association("ResellerGroup", remote_id=remote_data["teams"][0]["id"])
    if group is not None:
        data = {
            "group_id": group.local_id,
            "email": remote_data["email"],
            "number": "",
            "access_key": "",
            "phone": remote_data["phone"]
        }

    return data


def run_import():

    remote_groups = get("teams", {"limit": 1000})
    group_name_translation = {
        "TS Verkauf": "TS Solar",
        "KEZ": "KEZ",
        "HV": "KEZ",
        "HDV 1": "HV",
        "HDV 2": "HV",
        "HDV 3": "HV",
        "HDV 4": "HV",
        "HDV 5": "HV",
        "HDV 6": "HV",
        "HDV 7": "HV",
        "HDV 8": "HV",
    }
    for remote_group in remote_groups:
        local_group = db.session.query(ResellerGroup).filter(ResellerGroup.name == group_name_translation[remote_group["name"]]).first()
        if local_group is None:
            print(local_group)
        else:
            associate_item(model="ResellerGroup", local_id=local_group.id, remote_id=remote_group["id"])

    remote_users = get("users", {"limit": 1000})
    for remote_user in remote_users:
        local_user = db.session.query(Reseller).filter(Reseller.email == remote_user["email"]).first()
        if local_user is None:
            if len(remote_user["teams"]) > 0:
                item_data = filter_input(remote_user)
                if item_data is not None:
                    local_user = add_item(item_data)
        if local_user is not None:
            associate_item(model="Reseller", local_id=local_user.id, remote_id=remote_user["id"])
    return True
