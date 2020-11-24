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
from app.utils.data_convert import street_to_street_with_nb

from ._connector import get
from ._association import log_item, find_log


def get_import_data(raw):
    street, street_nb = street_to_street_with_nb(raw["street"])
    data = {
        "contact": {
            "salutation": "ms" if raw["title"] == "Frau" else "mr",
            "title": "",
            "first_name": raw["first_name"],
            "last_name": raw["last_name"],
            "street": street,
            "street_nb": street_nb,
            "zip": raw["zipcode"],
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
                    "VALUE": raw["phone"],
                    "TYPE_ID": "PHONE"
                }
            ]
        },
        "lead": {
            "title": f"{raw['first_name']} {raw['last_name']}, {raw['city']} (DAA)",
            "source_id": 3,
            "street": "",
            "street_nb": "",
            "zip": "",
            "city": ""
        },
        "timeline_comment": {
            "entity_type": "lead",
            "comment": raw["comment"]
        }
    }
    if "subject" in raw and "service" in raw:
        data["timeline_comment"]["comment"] = data["timeline_comment"]["comment"] \
            + f"Interesse an: {raw['subject']} {raw['service']}\n"
    if "infos" in raw:
        data["timeline_comment"]["comment"] = data["timeline_comment"]["comment"] \
            + f"Weitere Informationen:\n"
        for key in raw["infos"].keys():
            data["timeline_comment"]["comment"] = data["timeline_comment"]["comment"] \
                + f"{key}: {raw['infos'][key]}\n"
    return data


def run_cron_import():
    config = get_settings("external/daa")
    print("import leads daa")
    if config is None:
        print("no config for daa import")
        return None

    highest = 5315628
    if "last_import_id" in config:
        leads = get("/api/v2/leads/bought", parameters={
            "start_sale_id": config["last_import_id"]
        })
        highest = config["last_import_id"]
    else:
        leads = get("/api/v2/leads/bought", parameters={
            "start_sale_id": highest
        })
    if leads is not None:
        for lead in leads:
            if highest < int(lead["sale_id"]):
                highest = lead["sale_id"]
            log = find_log("Lead", identifier=lead["sale_id"])
            if log is not None:
                print("already imported:", lead["sale_id"])
                continue

            data = get_import_data(lead)
            existing_contact = get_contact_by_email(lead["email"])
            data["lead"]["category_id"] = 1
            if existing_contact is None:
                data["lead"]["stage_id"] = "C1:NEW"
                contact = add_contact(data["contact"])
                data["lead"]["contact_id"] = contact["id"]

                if "company" in data:
                    data["company"]["contact_id"] = contact["id"]
                    company = add_company(data["company"])
                    data["lead"]["company_id"] = company["id"]

                lead = add_lead(data["lead"])

                data["timeline_comment"]["entity_id"] = lead["id"]
                add_timeline_comment(data["timeline_comment"])

                auto_assign_lead_to_user(lead["id"])
            else:
                print("already known", existing_contact["id"])

                data["lead"]["stage_id"] = "C1:16"
                data["lead"]["contact_id"] = existing_contact["id"]
                lead = add_lead(data["lead"])

                data["timeline_comment"]["entity_id"] = lead["id"]
                add_timeline_comment(data["timeline_comment"])
            log_item("Lead", lead["sale_id"])
        config = get_settings("external/daa")
        if config is not None:
            config["last_import_id"] = highest
        set_settings("external/daa", config)
