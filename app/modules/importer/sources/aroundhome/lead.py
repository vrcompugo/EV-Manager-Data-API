import pprint
import time
import json
import random
from datetime import datetime, timedelta
from sqlalchemy import and_

from app import db
from app.models import Lead, Customer
from app.modules.lead.lead_services import add_item
from app.modules.customer.services.customer_services import add_item as customer_add_item
from app.modules.settings.settings_services import get_one_item as get_config_item, update_item as update_config_item
from app.utils.error_handler import error_handler

from ._connector import post, get
from ._association import find_association, associate_item


def filter_import_input(item_data):

    customer_id = None
    customer = None
    customer_accociation = find_association("Customer", remote_id=item_data["lead_id"])
    if customer_accociation is None:
        customer = run_customer_import(item_data)
        if customer is not None:
            customer_id = customer.id
    else:
        customer_id = customer_accociation.local_id
        customer = Customer.query.get(customer_accociation.local_id)

    reseller_id = None
    item_data["Quelle"] = "aroundhome"
    data = {
        "datetime": item_data["bought_at"],
        "last_update": item_data["bought_at"],
        "reseller_id": reseller_id,
        "customer_id": customer_id,
        "value": 25000,
        "status": "new",
        "data": item_data,
        "contact_source": "aroundhome",
        "description": item_data["calling_notes"]
    }
    if "answered_questions" in item_data:
        for attribute in item_data["answered_questions"]:
            data["description"] = data["description"] + attribute["question"] + ": "
            for answer in attribute["answers"]:
                data["description"] = data["description"] + answer["answer"] + " "
            data["description"] = data["description"] + "\n"
    data["description_html"] = data["description"].replace("\n", "<br>\n")
    if customer is not None and customer.default_address is not None:
        data["address_id"] = customer.default_address.id
    return data


def filter_customer_import_input(item_data):

    data = {
        "reseller_id": None,
        "customer_number": None,
        "lead_number": None,
        "company": "",
        "salutation": "ms" if item_data["offer_contact"]["salutation"] == "Frau" else "mr",
        "title": "",
        "firstname": item_data["offer_contact"]["first_name"],
        "lastname": item_data["offer_contact"]["last_name"],
        "email": item_data["offer_contact"]["email"],
        "phone": item_data["offer_contact"]["phone"],
        "pending_email": None,
        "email_status": None,
        "default_address": {
            "company": "",
            "salutation": "ms" if item_data["offer_contact"]["salutation"] == "Frau" else "mr",
            "title": "",
            "firstname": item_data["offer_contact"]["first_name"],
            "lastname": item_data["offer_contact"]["last_name"],
            "street": item_data["offer_contact"]["address"],
            "zip": item_data["offer_contact"]["zip_code"],
            "city": item_data["offer_contact"]["city"],
            "status": "ok"
        }
    }
    return data


def run_customer_import(lead):
    data = filter_customer_import_input(lead)
    if data is not None:
        customer = customer_add_item(data)
        associate_item("Customer", remote_id=lead["lead_id"], local_id=customer.id)
        return customer
    return None


def run_cron_import():
    from app.modules.lead.lead_services import lead_reseller_auto_assignment
    from app.utils.error_handler import error_handler
    config = get_config_item("importer/aroundhome")
    print("import leads aroundhome ")
    if config is None:
        print("no config for aroundhome import")
        return None
    import_time = datetime.now()
    if "data" in config and "last_lead_import_time" in config["data"]:
        leads = get("/v201609/leads", parameters={
            "from_datetime": str(config["data"]["last_lead_import_time"]),
            "per_page": 10000
        })
    else:
        leads = get("/v201609/leads", parameters={
            "per_page": 10000
        })

    if leads is not None:
        for lead in leads:
            link = find_association("Lead", remote_id=lead["lead_id"])
            if link is not None:
                continue
            if lead["offer_contact"]["email"] == "":
                lead["offer_contact_org"] = lead["offer_contact"]
                lead["offer_contact"] = lead["installation_contact"]
            existing = Customer.query.filter(Customer.email == lead["offer_contact"]["email"]).first()
            if existing is None:
                try:
                    data = filter_import_input(lead)
                    print(json.dumps(data, indent=2))
                    item = add_item(data)
                    lead_reseller_auto_assignment(item)
                    associate_item("Lead", remote_id=lead["lead_id"], local_id=item.id)
                except Exception as e:
                    error_handler()
            else:
                print("already known", lead["offer_contact"]["email"])
        config = get_config_item("importer/aroundhome")
        if config is not None and "data" in config:
            config["data"]["last_lead_import_time"] = str(import_time)
        update_config_item("importer/aroundhome", config)
