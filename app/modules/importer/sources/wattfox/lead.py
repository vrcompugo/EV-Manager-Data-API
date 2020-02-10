from app import db
import json
import time
import random
from datetime import datetime, timedelta
from sqlalchemy import and_

from app.models import Lead, Customer
from app.modules.lead.lead_services import add_item
from app.modules.customer.services.customer_services import add_item as customer_add_item
from app.modules.settings.settings_services import get_one_item as get_config_item, update_item as update_config_item

from ._connector import get
from ._association import find_association, associate_item


def filter_import_input(item_data):

    customer_id = None
    customer = None
    customer_accociation = find_association("Customer", remote_id=item_data["leadid"])
    if customer_accociation is None:
        customer = run_customer_import(item_data)
        if customer is not None:
            customer_id = customer.id
    else:
        customer_id = customer_accociation.local_id
        customer = Customer.query.get(customer_accociation.local_id)

    reseller_id = None
    bought_datetime = datetime.fromtimestamp(item_data["tstamp_sold"])
    data = {
        "datetime": str(bought_datetime),
        "last_update": str(bought_datetime),
        "reseller_id": reseller_id,
        "customer_id": customer_id,
        "value": 25000,
        "status": "new",
        "data": item_data,
        "description": ""
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
        "salutation": "mr" if item_data["salutation"] == "Herr" else "ms",
        "title": "",
        "firstname": item_data["firstname"],
        "lastname": item_data["lastname"],
        "email": item_data["email"],
        "phone": item_data["phone"],
        "pending_email": None,
        "email_status": None,
        "default_address": {
            "company": "",
            "salutation": "mr" if item_data["salutation"] == "Herr" else "ms",
            "title": "",
            "firstname": item_data["firstname"],
            "lastname": item_data["lastname"],
            "street": item_data["street"],
            "zip": item_data["zip"],
            "city": item_data["city"],
            "status": "ok"
        }
    }
    return data


def run_customer_import(lead):
    data = filter_customer_import_input(lead)
    if data is not None:
        customer = customer_add_item(data)
        associate_item("Customer", remote_id=lead["leadid"], local_id=customer.id)
        return customer
    return None


def run_cron_import():
    config = get_config_item("importer/wattfox")
    print("import leads wattfox")
    if config is None:
        print("no config for wattfox import")
        return None
    last_import_datetime = datetime.now()
    if "data" in config and "last_import_datetime" in config["data"]:
        last_import = datetime.strptime(
            config["data"]["last_import_datetime"],
            '%Y-%m-%d %H:%M:%S.%f'
        ).timestamp()
        leads = get("/leads/", parameters={
            "start": int(last_import),
            "stop": int(last_import_datetime.timestamp())
        })
    else:
        leads = get("/leads/", parameters={
            "start": 0,
            "stop": int(last_import_datetime.timestamp())
        })
    if leads is not None and "data" in leads:
        for lead in leads["data"]:
            lead_link = find_association("Lead", remote_id=lead["leadid"])
            if lead_link is None:
                existing = Customer.query.filter(Customer.email == lead["email"]).first()
                if existing is None:
                    data = filter_import_input(lead)
                    item = add_item(data)
                    associate_item("Lead", remote_id=lead["leadid"], local_id=item.id)
                    lead_reseller_auto_assignment(item)
                else:
                    print("already known", lead["email"])

        config = get_config_item("importer/wattfox")
        if config is not None and "data" in config:
            config["data"]["last_import_datetime"] = str(last_import_datetime)
        update_config_item("importer/wattfox", config)
