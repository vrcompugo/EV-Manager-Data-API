import time
import json
import random
from datetime import datetime, timedelta

from app import db
from app.modules.user import auto_assign_lead_to_user
from app.modules.external.bitrix24.company import add_company
from app.modules.external.bitrix24.contact import get_contact_by_email, add_contact
from app.modules.external.bitrix24.lead import get_lead, add_lead
from app.modules.external.bitrix24.timeline_comment import add_timeline_comment
from app.modules.settings import get_settings, set_settings
from app.utils.error_handler import error_handler
from app.utils.data_convert import street_to_street_with_nb, internationalize_phonenumber

from ._connector import get
from ._association import log_item, find_log


def get_import_data(raw):
    street, street_nb = street_to_street_with_nb(raw["lead"]["homeAddress"]["street"])
    data = {
        "contact": {
            "salutation": "ms" if raw["lead"]["salutation"] == "Frau" else "mr",
            "title": raw["lead"]["title"],
            "first_name": raw["lead"]["firstName"],
            "last_name": raw["lead"]["lastName"],
            "street": street,
            "street_nb": street_nb,
            "zip": raw["lead"]["homeAddress"]["postalCode"],
            "city": raw["lead"]["homeAddress"]["city"],
            "email": [
                {
                    "VALUE_TYPE": "WORK",
                    "VALUE": raw["lead"]["email"],
                    "TYPE_ID": "EMAIL"
                }
            ],
            "phone": [
                {
                    "VALUE_TYPE": "WORK",
                    "VALUE": internationalize_phonenumber(raw["lead"]["telephone"]),
                    "TYPE_ID": "PHONE"
                }
            ]
        },
        "lead": {
            "title": f"{raw['lead']['firstName']} {raw['lead']['lastName']}, {raw['lead']['homeAddress']['city']} (Senec)",
            "source_id": 3,
            "first_name": raw["lead"]["firstName"],
            "last_name": raw["lead"]["lastName"],
            "street": street,
            "street_nb": street_nb,
            "zip": raw["lead"]["homeAddress"]["postalCode"],
            "city": raw["lead"]["homeAddress"]["city"]
        },
        "timeline_comment": {
            "entity_type": "lead",
            "comment": ""
        }
    }

    if "companyName" in raw['lead'] and raw['lead']['companyName'] != "":
        data["company"] = {
            "company": raw['lead']['companyName'],
            "street": data["contact"]["street"],
            "street_nb": data["contact"]["street_nb"],
            "zip": data["contact"]["zip"],
            "city": data["contact"]["city"],
            "email": data["contact"]["email"],
            "phone": data["contact"]["phone"]
        }
    if "message" in raw['lead']:
        data["timeline_comment"]["comment"] = data["timeline_comment"]["comment"] + "Nachricht: " + str(raw['lead']["message"]) + "\n"
    if "reachability" in raw['lead']:
        data["timeline_comment"]["comment"] = data["timeline_comment"]["comment"] + "Erreichbarkeit: " + str(raw['lead']["reachability"]) + "\n"
    if "powerConsumption" in raw['lead']:
        data["timeline_comment"]["comment"] = data["timeline_comment"]["comment"] + "Verbrauch: " + str(raw['lead']["powerConsumption"]) + "\n"
    if "survey" in raw['lead']:
        for item in raw['lead']["survey"]["data"]:
            if isinstance(item, str):
                data["timeline_comment"]["comment"] = data["timeline_comment"]["comment"] \
                    + item + "\n"
            elif isinstance(item, list):
                data["timeline_comment"]["comment"] = data["timeline_comment"]["comment"] \
                    + " ".join(item) + "\n"
            else:
                data["timeline_comment"]["comment"] = data["timeline_comment"]["comment"] \
                    + item["question"] + " " + item["answer"] + "\n"
    return data


def run_cron_import():
    config = get_settings("external/senec")
    print("import leads senec")
    if config is None:
        print("no config for senec import")
        return None

    last_import_datetime = datetime.now()
    if "last_import_datetime" in config:
        leads = get("/assignments", parameters={
            "assignedFrom": config["last_import_datetime"],
            "limit": 1000
        })
    else:
        leads = get("/assignments", parameters={
            "assignedFrom": "2020-11-01",
            "limit": 1000
        })
    if leads is not None:
        for lead in leads:
            log = find_log("Lead", identifier=lead["assignment"]["id"])
            if log is not None:
                print("already imported:", lead["assignment"]["id"], lead["lead"]["email"])
                continue

            data = get_import_data(lead)
            existing_contact = get_contact_by_email(lead["lead"]["email"])
            if existing_contact is None:
                data["lead"]["status_id"] = "NEW"
                contact = add_contact(data["contact"])
                if contact not in [None, False]:
                    data["lead"]["contact_id"] = contact["id"]

                    if "company" in data:
                        data["company"]["contact_id"] = contact["id"]
                        company = add_company(data["company"])
                        data["lead"]["company_id"] = company["id"]

                lead_data = add_lead(data["lead"])

                data["timeline_comment"]["entity_id"] = lead_data["id"]
                add_timeline_comment(data["timeline_comment"])

                auto_assign_lead_to_user(lead_data["id"])
            else:
                print("already known", existing_contact["id"])

                data["lead"]["status_id"] = "14"
                data["lead"]["contact_id"] = existing_contact["id"]
                lead_data = add_lead(data["lead"])

                data["timeline_comment"]["entity_id"] = lead_data["id"]
                add_timeline_comment(data["timeline_comment"])
            log_item("Lead", lead["assignment"]["id"])
        config = get_settings("external/senec")
        if config is not None:
            config["last_import_datetime"] = last_import_datetime.strftime("%Y-%m-%d") + " 00:00:00"
        set_settings("external/senec", config)
