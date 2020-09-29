import pprint
import time
import json
import random
from datetime import datetime, timedelta
from sqlalchemy import and_

from app import db
from app.models import Customer
from app.modules.settings.settings_services import get_one_item as get_config_item, update_item as update_config_item
from app.utils.error_handler import error_handler

from ._connector import get, post, put
from ._association import find_association, associate_item


def filter_export_input(customer: Customer):
    data = {
        "LastName": customer.lastname,
        "FirstName": customer.firstname,
        "Email": customer.email,
        "loginid": customer.email,
        "Phone": customer.phone,
        "Salutation": "Frau" if customer.salutation == "ms" else "Herr",
        "Street": f"{customer.default_address.street} {customer.default_address.street_nb}",
        "ZIP": customer.default_address.zip,
        "City": customer.default_address.city
    }
    if customer.company is not None and customer.company != "":
        data["LastName"] = customer.company
        data["FirstName"] = ""
    return data


def run_cron_export():
    config = get_config_item("importer/etermin")
    print("import leads etermin ")
    if config is None:
        print("no config for etermin import")
        return None

    customers = None
    last_export_time = datetime.now()
    if "data" in config and "last_export_time" in config["data"]:
        customers = Customer.query.filter(Customer.last_change >= config["data"]["last_export_time"]).all()
    else:
        customers = Customer.query.all()
    if customers is not None:
        for customer in customers:
            customer_link = find_association("Customer", local_id=customer.id)
            print("export etermin customer", customer.id)
            if customer_link is None:
                data = filter_export_input(customer)
                result = post("/api/contact", data)
                if result is not None and "cid" in result:
                    associate_item("Customer", remote_id=result["cid"], local_id=customer.id)
            else:
                data = filter_export_input(customer)
                data["cid"] = customer_link.remote_id
                result = put("/api/contact", data)

        config = get_config_item("importer/etermin")
        if config is not None and "data" in config:
            config["data"]["last_export_time"] = str(last_export_time)
        update_config_item("importer/etermin", config)
