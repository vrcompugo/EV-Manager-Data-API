from app import db
import pprint

from app.models import Customer
from app.modules.lead.lead_services import add_item, update_item

from ._connector import post, get
from ._association import find_association, associate_item
from ..orgamaxx.customer import import_by_lead_number


def filter_input(item_data):
    if item_data["extended_info"]["fields_by_name"]["Interessenten-Nr."] == "":
        return None
    customer = db.session.query(Customer)\
        .filter(Customer.lead_number == str(item_data["extended_info"]["fields_by_name"]["Interessenten-Nr."]))\
        .first()
    if customer is None:
        customer = import_by_lead_number(item_data["extended_info"]["fields_by_name"]["Interessenten-Nr."])

    reseller_accociation = find_association("Reseller", remote_id=item_data["user_id"])
    if reseller_accociation is None:
        return None

    data = {
        "reseller_id": reseller_accociation.local_id,
        "customer_id": customer.id,
        "value": item_data["amount"],
        "number": item_data["id"],
        "status": item_data["step"]
    }
    if customer.default_address is not None:
        data["address_id"] = customer.default_address.id
    return data


def run_import():
    pp = pprint.PrettyPrinter(indent=2)

    items = get("leads", {
        "limit": 1,
        "offset": 0,
        "order": "last_update",
        "direction": "desc",
        "step": "Neu"
    })
    for item_data in items:
        item_data = get("leads/{}".format(item_data["id"]))
        lead_association = find_association("Lead", remote_id=item_data["id"])
        if lead_association is None:
            add_item(filter_input(item_data))
        else:
            update_item(lead_association.remote_id, filter_input(item_data))
    return False
