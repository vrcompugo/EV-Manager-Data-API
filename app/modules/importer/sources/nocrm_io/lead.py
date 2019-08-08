from app import db
import pprint
from datetime import datetime, timedelta

from app.models import Customer, Lead, S3File
from app.modules.lead.lead_services import add_item, update_item

from ._connector import post, get, put
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
    if customer is None:
        print("customer: ", item_data["extended_info"]["fields_by_name"]["Interessenten-Nr."])
        return None

    reseller_accociation = find_association("Reseller", remote_id=item_data["user_id"])
    if reseller_accociation is None:
        print("reseller: ", item_data["user_id"])
        reseller_id = None
    else:
        reseller_id = reseller_accociation.local_id

    status = "new"
    if item_data["step"] == "Kontaktiert":
        status = "contacted"
    if item_data["step"] == "Analyse durchgeführt":
        status = "survey_created"
    if item_data["step"] == "Angebot erstellt":
        status = "offer_created"
    if item_data["step"] == "Angebot präsentiert":
        status = "offer_presented"
    if item_data["step"] == "Vertragsverhandlung":
        status = "offer_negotiation"
    if item_data["step"] == "Verloren":
        status = "lost"
    if item_data["step"] == "Verkauft":
        status = "won"

    data = {
        "datetime": item_data["created_at"],
        "last_update": item_data["updated_at"],
        "reminder_datetime": item_data["reminder_at"],
        "reseller_id": reseller_id,
        "customer_id": customer.id,
        "value": item_data["amount"],
        "number": item_data["extended_info"]["fields_by_name"]["Interessenten-Nr."],
        "status": status,
        "data": item_data["extended_info"]["fields_by_name"],
        "description": item_data["description"],
        "description_html": item_data["html_description"]
    }
    if customer.default_address is not None:
        data["address_id"] = customer.default_address.id
    return data


def run_import(minutes=None):
    print("Loading Lead List")
    load_more = True
    offset = 0
    limit = 100
    options = {
        "order": "last_update",
        "direction": "desc"
    }
    if minutes is not None:
        options["updated_after"] = datetime.now() - timedelta(minutes=minutes)
    while load_more:
        options["limit"] = limit
        options["offset"] = offset
        items = get("leads", options)
        load_more = len(items) == limit
        offset = offset + limit
        print("Count: ", len(items))
        print("Offset: ", offset)

        for item_data in items:
            item_data = get("leads/{}".format(item_data["id"]))
            lead_association = find_association("Lead", remote_id=item_data["id"])
            if lead_association is None:
                data = filter_input(item_data)

                if data is not None:
                    item = add_item(data)
                    associate_item(model="Lead", local_id=item.id, remote_id=item_data["id"])
                    print("success", item.id)
                else:
                    print(item_data["id"], item_data["extended_info"]["fields_by_name"]["Interessenten-Nr."], item_data["user_id"], item_data["extended_info"]["user"]["email"])
            else:
                data = filter_input(item_data)
                if data is not None:
                    update_item(lead_association.local_id, data)
    return False
