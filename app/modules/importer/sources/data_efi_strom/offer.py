from app import db
from app.models import Contract
from app.modules.offer.offer_services import add_item , update_item

from ._connector import post
from ._association import find_association, associate_item


def filter_input(data):

    item = find_association(model="Product", remote_id=data["form_id"])
    data["product_id"] = item.local_id if item is not None else None

    item = find_association(model="Customer", remote_id=data["customer_id"])
    data["customer_id"] = item.local_id if item is not None else None
    if "customer" in data:
        del data["customer"]

    item = find_association(model="CustomerAddress", remote_id=data["customer_address_id"])
    data["address_id"] = item.local_id if item is not None else None

    item = find_association(model="CustomerPaymentAccount", remote_id=data["customer_payment_info_id"])
    data["payment_account_id"] = item.local_id if item is not None else None

    item = find_association(model="Reseller", remote_id=data["reseller_id"])
    data["reseller_id"] = item.local_id if item is not None else None
    if "reseller" in data:
        del data["reseller"]

    if data["status"] is None or data["status"] == "":
        data["offer_status"] = "open"
    if data["status"] == "sent":
        data["offer_status"] = "created"
    if data["status"] == "missing_documents":
        data["offer_status"] = "missing_data"

    return data


def run_import():
    data = post("Offer", {"page": 0, "limit": 1000})
    if "items" in data:
        for item_data in data["items"]:

            item_data = filter_input(item_data)

            item = find_association(model="Offer", remote_id=item_data["id"])
            if item is None:
                item = add_item(item_data)
                if item is not None:
                    associate_item(model="Offer", remote_id=item_data["id"], local_id=item.id)
            else:
                update_item(id=item.local_id, data=item_data)

    return False
