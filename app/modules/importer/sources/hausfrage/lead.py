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

from ._connector import post
from ._association import find_association, associate_item


def filter_import_input(item_data):

    customer_id = None
    customer = None
    customer_accociation = find_association("Customer", remote_id=item_data["sale_id"])
    if customer_accociation is None:
        customer = run_customer_import(item_data)
        if customer is not None:
            customer_id = customer.id
    else:
        customer_id = customer_accociation.local_id
        customer = Customer.query.get(customer_accociation.local_id)

    reseller_id = None
    item_data["Quelle"] = "Hausfrage"
    data = {
        "datetime": item_data["Distributed"],
        "last_update": item_data["Distributed"],
        "reseller_id": reseller_id,
        "customer_id": customer_id,
        "value": 25000,
        "status": "new",
        "data": item_data,
        "contact_source": "Hausfrage",
        "description": ""
    }
    if "LeadAttributeValues" in item_data:
        for attribute in item_data["LeadAttributeValues"]:
            data["description"] = data["description"] + attribute["Attribute"] + ": " + attribute["Value"] + "\n"
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
        "salutation": "mr" if item_data["Salutation"] == "Herr" else "ms",
        "title": "",
        "firstname": item_data["Firstname"],
        "lastname": item_data["Lastname"],
        "email": item_data["Email"],
        "phone": item_data["Phone"],
        "pending_email": None,
        "email_status": None,
        "default_address": {
            "company": "",
            "salutation": "mr" if item_data["Salutation"] == "Herr" else "ms",
            "title": "",
            "firstname": item_data["Firstname"],
            "lastname": item_data["Lastname"],
            "street": item_data["Street"],
            "zip": item_data["Zipcode"],
            "city": item_data["City"],
            "status": "ok"
        }
    }
    return data


def run_customer_import(lead):
    data = filter_customer_import_input(lead)
    if data is not None:
        customer = customer_add_item(data)
        associate_item("Customer", remote_id=lead["sale_id"], local_id=customer.id)
        return customer
    return None


def run_cron_import():
    from app.modules.lead.lead_services import lead_reseller_auto_assignment
    from app.utils.error_handler import error_handler
    config = get_config_item("importer/hausfrage")
    print("import leads hausfrage ")
    if config is None:
        print("no config for hausfrage import")
        return None
    import_time = datetime.now()
    if "data" in config and "last_lead_import_time" in config["data"]:
        leads = post("/Applications/Leads.ashx", parameters={
            "Action": "ACTION_PICKUP_LEADS",
            "Start": str(config["data"]["last_lead_import_time"]),
            "End": str(import_time)
        })
    else:
        leads = post("/Applications/Leads.ashx", parameters={
            "Action": "ACTION_PICKUP_LEADS",
            "Start": "1970-01-01 00:00:00",
            "End": str(import_time)
        })

    print(json.dumps(leads["Leads"], indent=2))
    return
    if leads is not None:
        for lead in leads["Leads"]:
            existing = Customer.query.filter(Customer.email == lead["email"]).first()
            if existing is None:
                try:
                    data = filter_import_input(lead)
                    item = add_item(data)
                    lead_reseller_auto_assignment(item)
                except Exception as e:
                    error_handler()
            else:
                print("already known", lead["email"])

        config = get_config_item("importer/hausfrage")
        if config is not None and "data" in config:
            config["data"]["last_lead_import_time"] = import_time
        update_config_item("importer/hausfrage", config)
