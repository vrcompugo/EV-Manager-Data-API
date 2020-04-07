from app import db
import pprint
import time
import random
from datetime import datetime, timedelta
from sqlalchemy import and_

from app.models import Lead, Customer
from app.modules.lead.lead_services import add_item
from app.modules.customer.services.customer_services import add_item as customer_add_item
from app.modules.settings.settings_services import get_one_item as get_config_item, update_item as update_config_item
from app.utils.error_handler import error_handler

from ._connector import get
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
    item_data["Quelle"] = "DAA"
    data = {
        "datetime": item_data["sale_date"],
        "last_update": item_data["sale_date"],
        "reseller_id": reseller_id,
        "customer_id": customer_id,
        "value": 25000,
        "status": "new",
        "data": item_data,
        "contact_source": "DAA",
        "description": item_data["comment"]
    }
    data["description_html"] = data["description"].replace("\n", "<br>\n")
    if customer is not None and customer.default_address is not None:
        data["address_id"] = customer.default_address.id
    return data


def filter_customer_import_input(item_data):

    reseller_id = None
    data = {
        "reseller_id": reseller_id,
        "customer_number": None,
        "lead_number": None,
        "company": "",
        "salutation": "mr" if item_data["title"] == "Herr" else "ms",
        "title": "",
        "firstname": item_data["first_name"],
        "lastname": item_data["last_name"],
        "email": item_data["email"],
        "phone": item_data["phone"],
        "pending_email": None,
        "email_status": None,
        "default_address": {
            "company": "",
            "salutation": "mr" if item_data["title"] == "Herr" else "ms",
            "title": "",
            "firstname": item_data["first_name"],
            "lastname": item_data["last_name"],
            "street": item_data["street"],
            "zip": item_data["zipcode"],
            "city": item_data["city"],
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
    config = get_config_item("importer/daa")
    print("import leads daa ")
    if config is None:
        print("no config for daa import")
        return None
    if "data" in config and "last_import_id" in config["data"]:
        leads = get("/api/v2/leads/bought", parameters={
            "start_sale_id": config["data"]["last_import_id"]
        })
        highest = config["data"]["last_import_id"]
    else:
        leads = get("/api/v2/leads/bought")
        highest = 0

    if leads is not None:
        for lead in leads:
            lead_link = find_association("Lead", remote_id=lead["sale_id"])
            if lead_link is None:
                existing = Customer.query.filter(Customer.email == lead["email"]).first()
                if existing is None:
                    if highest < lead["sale_id"]:
                        highest = lead["sale_id"]
                    try:
                        data = filter_import_input(lead)
                        item = add_item(data)
                        associate_item("Lead", remote_id=lead["sale_id"], local_id=item.id)
                        if "subject" in lead.data:
                            if lead.data["subject"] in ["heat_pump", "gas_heating", "oil_heating"]:
                                lead.reseller_id = 10
                        lead_reseller_auto_assignment(item)
                    except Exception as e:
                        error_handler()
                else:
                    print("already known", lead["email"])

        config = get_config_item("importer/daa")
        if config is not None and "data" in config:
            config["data"]["last_import_id"] = highest
        update_config_item("importer/daa", config)
