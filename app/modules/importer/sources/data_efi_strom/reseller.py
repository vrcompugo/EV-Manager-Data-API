from app import db
from app.modules.reseller.services.reseller_services import add_item , update_item
from app.modules.reseller.services.reseller_group_services import add_item as group_add_item, update_item as group_update_item
from app.modules.reseller.models.reseller import Reseller

from ._connector import post
from ._association import find_association, associate_item


def filter_input_group(data):

    data["products"] = data["forms"]

    return data


def filter_input_reseller(data):

    item = find_association(model="ResellerGroup", remote_id=data["group_id"])
    data["group_id"] = item.local_id if item is not None else None
    del data["group"]
    return data


def run_import():
    data = post("ResellerGroup")
    if "items" in data:
        for item_data in data["items"]:

            item_data = filter_input_group(item_data)
            item = find_association(model="ResellerGroup", remote_id=item_data["id"])
            if item is None:
                item = group_add_item(item_data)
                if item is not None:
                    associate_item(model="ResellerGroup", remote_id=item_data["id"], local_id=item.id)
            else:
                group_update_item(id=item.local_id, data=item_data)

    data = post("Reseller")
    if "items" in data:
        for item_data in data["items"]:

            item_data = filter_input_reseller(item_data)
            item = find_association(model="Reseller", remote_id=item_data["id"])
            if item is None:
                reseller = db.session.query(Reseller).filter(Reseller.email == item_data["email"]).first()
                if reseller is None:
                    item = add_item(item_data)
                    if item is not None:
                        associate_item(model="Reseller", remote_id=item_data["id"], local_id=item.id)
                else:
                    associate_item(model="Reseller", remote_id=item_data["id"], local_id=reseller.id)
            else:
                update_item(id=item.local_id, data=item_data)
    return False
