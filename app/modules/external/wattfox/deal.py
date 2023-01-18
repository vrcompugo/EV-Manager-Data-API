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
    street, street_nb = street_to_street_with_nb(raw["street"])
    data = {
        "contact": {
            "salutation": "ms" if raw["salutation"] == "Frau" else "mr",
            "title": "",
            "first_name": raw["firstname"],
            "last_name": raw["lastname"],
            "street": street,
            "street_nb": street_nb,
            "zip": raw["zip"],
            "city": raw["city"],
            "email": [
                {
                    "VALUE_TYPE": "WORK",
                    "VALUE": raw["email"],
                    "TYPE_ID": "EMAIL"
                }
            ],
            "phone": [
                {
                    "VALUE_TYPE": "WORK",
                    "VALUE": internationalize_phonenumber(raw["phone"]),
                    "TYPE_ID": "PHONE"
                }
            ]
        },
        "lead": {
            "title": f"{raw['firstname']} {raw['lastname']}, {raw['city']} (Wattfox)",
            "source_id": "2",
            "first_name": raw["firstname"],
            "last_name": raw["lastname"],
            "street": street,
            "street_nb": street_nb,
            "zip": raw["zip"],
            "city": raw["city"]
        },
        "timeline_comment": {
            "entity_type": "lead",
            "comment": ""
        }
    }
    if "company" in raw and raw['company'] != "":
        data["company"] = {
            "company": raw['company'],
            "street": data["contact"]["street"],
            "street_nb": data["contact"]["street_nb"],
            "zip": data["contact"]["zip"],
            "city": data["contact"]["city"],
            "email": data["contact"]["email"],
            "phone": data["contact"]["phone"]
        }
    if "notes" in raw:
        data["timeline_comment"]["comment"] = data["timeline_comment"]["comment"] + "Bemerkung: " + str(raw["notes"]) + "\n"
    if "lead_product_name" in raw:
        data["timeline_comment"]["comment"] = data["timeline_comment"]["comment"] + "Produkt: " + str(raw["lead_product_name"]) + "\n"
    if "availability" in raw:
        data["timeline_comment"]["comment"] = data["timeline_comment"]["comment"] + "Erreichbarkeit: " + str(raw["availability"]) + "\n"
    if "implementation" in raw:
        data["timeline_comment"]["comment"] = data["timeline_comment"]["comment"] + "Wunsch Zeitraum: " + str(raw["implementation"]) + "\n"
    if "stromverbrauch" in raw:
        data["timeline_comment"]["comment"] = data["timeline_comment"]["comment"] + "Stromverbrauch: " + str(raw["stromverbrauch"]) + "\n"
    for key in raw.keys():
        if key[:3] == "ph_":
            data["timeline_comment"]["comment"] = data["timeline_comment"]["comment"] + str(key[3:]) + ": " + str(raw[key]) + "\n"
    return data


def run_cron_import():
    config = get_settings("external/wattfox")
    print("import leads wattfox")
    if config is None:
        print("no config for wattfox import")
        return None

    last_import_datetime = datetime.now()
    if "last_import_datetime" in config:
        last_import = datetime.strptime(
            config["last_import_datetime"],
            '%Y-%m-%d %H:%M:%S.%f'
        ).timestamp()
        leads = get("/leads/", parameters={
            "start": int(last_import),
            "stop": int(last_import_datetime.timestamp())
        })
    else:
        leads = get("/leads/", parameters={
            "start": int(datetime(2020, 11, 1, 0, 0, 0).timestamp()),
            "stop": int(last_import_datetime.timestamp())
        })
    print("wattfox leads", leads)
    if leads is not None:
        for lead in leads["data"]:
            log = find_log("Lead", identifier=lead["wf_leadid"])
            if log is not None:
                print("already imported:", lead["wf_leadid"])
                continue

            data = get_import_data(lead)
            existing_contact = get_contact_by_email(lead["email"])
            if existing_contact is None:
                data["lead"]["status_id"] = "NEW"
                contact = add_contact(data["contact"])
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
            log_item("Lead", lead["wf_leadid"])
        config = get_settings("external/wattfox")
        if config is not None:
            config["last_import_datetime"] = str(last_import_datetime)
        set_settings("external/wattfox", config)
