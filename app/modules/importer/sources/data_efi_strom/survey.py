from app import db
from app.modules.survey.survey_services import add_item , update_item

from ._connector import post
from ._association import find_association, associate_item


def filter_input(data):

    item = find_association(model="Customer", remote_id=data["customer_id"])
    data["customer_id"] = item.local_id if item is not None else None
    del data["customer"]

    item = find_association(model="CustomerAddress", remote_id=data["address_id"])
    data["address_id"] = item.local_id if item is not None else None

    item = find_association(model="Reseller", remote_id=data["reseller_id"])
    data["reseller_id"] = item.local_id if item is not None else None
    del data["reseller"]

    data["data_status"] = "complete" if data["status"] == "send" else "incomplete"
    if data["offer_status"] is None or data["offer_status"] == "":
        data["offer_status"] = "open"
    if data["offer_status"] == "sent":
        data["offer_status"] = "created"
    if data["offer_status"] == "missing_documents":
        data["offer_status"] = "missing_data"

    return data


def run_import():
    data = post("Survey", {"page": 0, "limit": 1000})
    if "items" in data:
        for item_data in data["items"]:

            item_data = filter_input(item_data)

            item = find_association(model="Survey", remote_id=item_data["id"])
            if item is None:
                item = add_item(item_data)
                if item is not None:
                    associate_item(model="Survey", remote_id=item_data["id"], local_id=item.id)
            else:
                update_item(id=item.local_id, data=item_data)

    return False
