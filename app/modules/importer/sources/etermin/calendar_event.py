from app import db
import pprint
import time
import random
import json
from datetime import datetime, timedelta
from sqlalchemy import and_

from app.models import CalendarEvent, Customer
from app.modules.calendar.calendar_services import add_item, update_item
from app.modules.settings.settings_services import get_one_item as get_config_item, update_item as update_config_item
from app.utils.error_handler import error_handler

from ._connector import get
from ._association import find_association, associate_item


def filter_import_data(item_data):
    customer_id = None
    if "Email" in item_data and item_data["Email"] != "":
        customer = Customer.query.filter(Customer.email == item_data["Email"]).first()
        if customer is not None:
            customer_id = customer.id
    data = {
        "customer_id": customer_id,
        "user_id": None,
        "reseller_id": None,
        "order_id": None,
        "task_id": None,
        "color": "",
        "label": "",
        "salutation": "ms" if item_data["Salutation"] == "Frau" else "mr",
        "title": item_data["Title"],
        "firstname": item_data["FirstName"],
        "lastname": item_data["LastName"],
        "company": "",
        "street": item_data["Street"],
        "street_nb": "",
        "zip": item_data["ZIP"],
        "city": item_data["Town"],
        "type": "",
        "begin": item_data["StartDateTime"],
        "end": item_data["EndDateTime"],
        "comment": item_data["Notes"],
        "status": "open"
    }
    return data


def run_import(remote_id=None, local_id=None, cid=None):
    if local_id is not None:
        event_link = find_association("CalendarEvent", local_id=local_id)
        print("online cron import possible")
        return None
    if remote_id is not None:
        print("importing CalendarEvent", remote_id)
        response = get("/api/appointment", parameters={
            "id": remote_id
        })
        if response is not None and len(response) > 0:
            data = filter_import_data(response[0])
            if data is not None:
                event_link = find_association("CalendarEvent", remote_id=cid)
                if event_link is None:
                    event = add_item(data)
                    associate_item(model="CalendarEvent", local_id=event.id, remote_id=cid)
                else:
                    event = update_item(event_link.local_id, data)
                return event
            else:
                print("data is not CalendarEvent import: ", response)
        else:
            print("no response", response)
    return None


def run_cron_import():
    from app.utils.error_handler import error_handler
    config = get_config_item("importer/etermin")
    print("import event etermin ")
    if config is None:
        print("no config for etermin import")
        return None
    if "data" in config and "last_event_import_date" in config["data"]:
        events = get("/api/appointment", parameters={
            "start": config["data"]["last_event_import_date"]
        })
    else:
        events = get("/api/appointment", parameters={
            "start": "2020-01-01"
        })
    today = datetime.today()
    last_import_date = today.strftime("%Y-%m-%d")
    if events is not None:
        for event in events:
            print("import event", event["ExternalID"])
            run_import(remote_id=event["ExternalID"], cid=event["ID"])

        config = get_config_item("importer/etermin")
        if config is not None and "data" in config:
            config["data"]["last_event_import_date"] = str(last_import_date)
        update_config_item("importer/etermin", config)
