from app import db
from app.models import Customer
from app.modules.customer.services.customer_services import merge_items

from ._connector import post
from ._association import find_association, associate_item


def filter_input(data):
    if "default_address_id" in data:
        address = find_association("CustomerAddress", remote_id=data["default_address_id"])
        if address is None:
            del data["default_address_id"]
        else:
            data["default_address_id"] = address.id

    if "default_paymentinfo_id" in data:
        account = find_association("CustomerPaymentAccount", remote_id=data["default_paymentinfo_id"])
        if account is None:
            del data["default_paymentinfo_id"]
        else:
            data["default_paymentinfo_id"] = account.id

    if "email" in data and data["email"] == "":
        data["email"] = None
    if "customer_number" in data and data["customer_number"] == "":
        data["customer_number"] = None
    if "lead_number" in data and data["lead_number"] == "":
        data["lead_number"] = None

    if "default_paymentinfo" in data:
        data["default_payment_account"] = {
            "id": data["default_paymentinfo"]["id"],
            "type": "bankaccount",
            "data": {
                "iban": data["default_paymentinfo"]["iban"],
                "bank": data["default_paymentinfo"]["bank"],
                "bic": data["default_paymentinfo"]["bic"]
            }
        }

    return data


def run_import():
    data = post("Customer")
    if "items" in data:
        for item_data in data["items"]:
            default_address_id = item_data["default_address_id"]
            default_paymentinfo_id = item_data["default_paymentinfo_id"]
            item_data = filter_input(item_data)

            item = find_association(model="Customer", remote_id=item_data["id"])
            if item is None:
                item = merge_items(item_data)
                if item is not None:
                    associate_item(model="Customer", remote_id=item_data["id"], local_id=item.id)
                    associate_item(model="CustomerAddress",
                                   remote_id=default_address_id,
                                   local_id=item.default_address.id)
                    associate_item(model="CustomerPaymentAccount",
                                   remote_id=default_paymentinfo_id,
                                   local_id=item.default_payment_account.id)
            else:
                customer = db.session.query(Customer).get(item.local_id)
                if customer.default_address is not None:
                    associate_item(model="CustomerAddress",
                                   remote_id=default_address_id,
                                   local_id=customer.default_address.id)
                if customer.default_payment_account is not None:
                    associate_item(model="CustomerPaymentAccount",
                                   remote_id=default_paymentinfo_id,
                                   local_id=customer.default_payment_account.id)
        return True
    return False
