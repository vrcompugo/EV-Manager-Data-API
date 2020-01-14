from app import db
import pprint
from datetime import datetime, timedelta

from app.models import Customer, Lead, Reseller
from app.modules.lead.lead_services import add_item, update_item
from app.modules.settings.settings_services import get_one_item as get_config_item, update_item as update_config_item
from app.modules.events.event_services import add_trigger

from ._connector import post, get, put, remote_user_id
from ._association import find_association, associate_item
from ..orgamaxx.customer import import_by_lead_number


def filter_input(item_data):
    if "Interessenten-Nr." not in item_data["extended_info"]["fields_by_name"] or \
            item_data["extended_info"]["fields_by_name"]["Interessenten-Nr."] == "" or \
            item_data["extended_info"]["fields_by_name"]["Interessenten-Nr."] is None:
        return None
    item_data["extended_info"]["fields_by_name"]["Interessenten-Nr."] = item_data["extended_info"]["fields_by_name"]["Interessenten-Nr."].strip()
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
    activities = []
    for activity in item_data["activities"]:
        activity_data = {
            "user_id": None,
            "datetime": activity["created_at"],
            "action": activity["action_type"],
            "action_data": activity["action_item"]
        }
        activity_accociation = find_association("LeadActivity", remote_id=activity["id"])
        if activity_accociation is not None:
            activity_data["id"] = activity_accociation.local_id
        user_accociation = find_association("Reseller", remote_id=item_data["user_id"])
        if user_accociation is not None:
            reseller = Reseller.query.filter(Reseller.id == user_accociation.local_id).first()
            activity_data["user_id"] = None if reseller is None else reseller.user_id
        activities.append(activity_data)

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
        "description_html": item_data["html_description"],
        "activities": activities
    }
    if customer.default_address is not None:
        data["address_id"] = customer.default_address.id
    return data


def filter_export_input(lead):

    if not lead.reseller_id > 0:
        return None

    reseller_link = find_association("Reseller", local_id=lead.reseller_id)
    if reseller_link is None:
        print("reseller doesn't exist at nocrm.io", lead.reseller_id)
        return None

    data = {
        "title": (lead.customer.company + " " + lead.customer.lastname).strip(),
        "description": lead.description,
        "user_id": reseller_link.remote_id,
        "amount": float(lead.value)
    }
    return data


def run_import(minutes=None, remote_id=None):
    if remote_id is not None:
        run_single_import(remote_id)
        return
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
    else:
        config = get_config_item("importer/nocrm_io")
        if config is not None and "data" in config and "last_import" in config["data"]:
            options["updated_after"] = config["data"]["last_import"]
    while load_more:
        options["limit"] = limit
        options["offset"] = offset
        items = get("leads", options)
        load_more = len(items) == limit
        offset = offset + limit
        print("Count: ", len(items))
        print("Offset: ", offset)

        for item_data in items:
            run_single_import(item_data["id"])

    if minutes is None:
        config = get_config_item("importer/nocrm_io")
        if config is not None and "data" in config:
            config["data"]["last_import"] = str(datetime.now())
        update_config_item("importer/nocrm_io", config)
    return True


def run_single_import(remote_id):
    item_data = get("leads/{}".format(remote_id))
    item_data["activities"] = get("leads/{}/action_histories".format(item_data["id"]))
    data = filter_input(item_data)
    if data is None:
        print(item_data["id"], item_data["extended_info"]["fields_by_name"]["Interessenten-Nr."],
              item_data["user_id"], item_data["extended_info"]["user"]["email"])
        return
    if data["reseller_id"] is not None and data["reseller_id"] in [47, 10, 17, 3, 12, 2, 59, 41]:
        return None
    lead_association = find_association("Lead", remote_id=item_data["id"])
    if lead_association is None:
        existing_lead = Lead.query.filter(Lead.number == data["number"]).first()
        if existing_lead is not None:
            associate_item(model="Lead", local_id=existing_lead.id, remote_id=item_data["id"])
            lead_association = find_association("Lead", remote_id=item_data["id"])
    if lead_association is None:
        item = add_item(data)
        associate_item(model="Lead", local_id=item.id, remote_id=item_data["id"])
        print("success", item.id)

    else:
        update_item(lead_association.local_id, data)


def run_export(remote_id=None, local_id=None):
    lead = None
    if local_id is not None:
        lead = Lead.query.get(local_id)
    if remote_id is not None:
        lead_association = find_association("Lead", remote_id=remote_id)
        lead = Lead.query.get(lead_association.local_id)
    if lead is not None:
        if len(lead.number) > 5:
            return
        post_data = filter_export_input(lead)
        if post_data is not None:
            lead_association = find_association("Lead", local_id=lead.id)
            if lead_association is None:
                response = post("leads", post_data=post_data)
                if "id" in response:
                    associate_item(model="Lead", local_id=lead.id, remote_id=response["id"])
                    post_data["id"] = response["id"]
                    put("leads/{}".format(post_data["id"]), post_data=post_data)
                    add_trigger({
                        "name": "lead_exported",
                        "data": {
                            "lead_id": lead.id,
                            "operation": "add",
                            "source": "nocrm.io"
                        }
                    })
                else:
                    print(response)
