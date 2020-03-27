from app import db
from app.modules.survey.survey_services import add_item , update_item

from ._connector import post, get
from ._association import find_association, associate_item
from .customer import run_single_import as run_single_customer_import


def filter_input(data):

    item = find_association(model="Customer", remote_id=data["customer_id"])
    if item is None:
        customer = run_single_customer_import(remote_id=data["customer_id"])
        if customer is None:
            return None
        data["customer_id"] = customer.id
    else:
        data["customer_id"] = item.local_id
    if "customer" in data:
        del data["customer"]

    item = find_association(model="CustomerAddress", remote_id=data["address_id"])
    data["address_id"] = item.local_id if item is not None else None

    item = find_association(model="Reseller", remote_id=data["reseller_id"])
    data["reseller_id"] = item.local_id if item is not None else None
    if "reseller" in data:
        del data["reseller"]

    data["data_status"] = "complete" if data["status"] == "send" else "incomplete"
    if data["offer_status"] is None or data["offer_status"] == "":
        data["offer_status"] = "open"
    if data["offer_status"] == "sent":
        data["offer_status"] = "created"
    if data["offer_status"] == "missing_documents":
        data["offer_status"] = "missing_data"

    if "data" in data and "lead_id" in data["data"]:
        data["lead_id"] = data["data"]["lead_id"]

    return data


def run_import(remote_id=None, local_id=None):
    if remote_id is not None:
        data = get("Survey/{}".format(remote_id))
        if "status" in data and data["status"] == "success":
            run_single_import(data["item"])
        return False
    data = post("Survey", {"page": 0, "limit": 1000})
    if "items" in data:
        for item_data in data["items"]:
            run_single_import(item_data)

    return False


def run_single_import(item_data):
    remote_id = item_data["id"]
    item_data = filter_input(item_data)
    if item_data is None:
        print("error item_data")
        return

    item = find_association(model="Survey", remote_id=remote_id)
    if item is None:
        item = add_item(item_data)
        if item is not None:
            associate_item(model="Survey", remote_id=remote_id, local_id=item.id)
    else:
        update_item(id=item.local_id, data=item_data)
