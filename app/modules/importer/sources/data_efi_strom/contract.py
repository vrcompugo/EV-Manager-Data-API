from app import db
from app.models import Customer
from app.modules.contract.contract_services import add_item , update_item

from ._connector import post
from ._association import find_association, associate_item


def filter_input(data):

    if "offer" in data:
        item = find_association(model="Offer", remote_id=data["offer"]["id"])
        data["offer_id"] = item.local_id if item is not None else None
        del data["offer"]
    else:
        data["offer_id"] = None

    item = find_association(model="Product", remote_id=data["form_id"])
    data["product_id"] = item.local_id if item is not None else None

    item = find_association(model="Customer", remote_id=data["customer_id"])
    data["customer_id"] = item.local_id if item is not None else None
    if "customer" in data:
        del data["customer"]
    customer = db.session.query(Customer).get(item.local_id)
    data["address_id"] = customer.default_address_id if customer is not None else None
    data["payment_account_id"] = customer.default_payment_account_id if customer is not None else None

    item = find_association(model="Reseller", remote_id=data["reseller_id"])
    data["reseller_id"] = item.local_id if item is not None else None
    if "reseller" in data:
        del data["reseller"]

    if data["kez_state"] is None:
        data["status"] = "open"
    if data["kez_state"] == "archive":
        data["status"] = "canceled"
    if data["kez_state"] == "delivery":
        data["status"] = "in_delivery"
    if data["kez_state"] == "missing_documents":
        data["status"] = "missing_documents"
    if data["kez_state"] == "waiting":
        data["status"] = "sent_to_ev"

    data["number"] = data["customer_number"]
    data["delivery_begin"] = None if data["delivery_begin"] == "None" else data["delivery_begin"]
    if "form" in data:
        del data["form"]
    if "customer_address" in data:
        del data["customer_address"]

    return data


def run_import():
    data = post("FormData", {"page": 0, "limit": 1000})
    if "items" in data:
        for item_data in data["items"]:

            item_data = filter_input(item_data)
            item = find_association(model="Contract", remote_id=item_data["id"])
            if item is None:
                item = add_item(item_data)
                if item is not None:
                    associate_item(model="Contract", remote_id=item_data["id"], local_id=item.id)
            else:
                update_item(id=item.local_id, data=item_data)

    return False
