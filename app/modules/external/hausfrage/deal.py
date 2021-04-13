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

from ._connector import post
from ._association import log_item, find_log


def get_import_data(raw):
    street, street_nb = street_to_street_with_nb(raw["Street"])
    data = {
        "contact": {
            "salutation": "ms" if raw["Salutation"] == "Frau" else "mr",
            "title": "",
            "first_name": raw["Firstname"],
            "last_name": raw["Lastname"],
            "street": street,
            "street_nb": street_nb,
            "zip": raw["Zipcode"],
            "city": raw["City"],
            "email": [
                {
                    "VALUE_TYPE": "WORK",
                    "VALUE": raw["Email"],
                    "TYPE_ID": "EMAIL"
                }
            ],
            "phone": [
                {
                    "VALUE_TYPE": "WORK",
                    "VALUE": internationalize_phonenumber(raw["Phone"]),
                    "TYPE_ID": "PHONE"
                }
            ]
        },
        "lead": {
            "title": f"{raw['Firstname']} {raw['Lastname']}, {raw['City']} (Hausfrage)",
            "source_id": 14,
            "first_name": raw["Firstname"],
            "last_name": raw["Lastname"],
            "street": street,
            "street_nb": street_nb,
            "zip": raw["Zipcode"],
            "city": raw["City"]
        },
        "timeline_comment": {
            "entity_type": "lead",
            "comment": ""
        }
    }
    if "LeadAttributeValues" in raw:
        for attribute in raw["LeadAttributeValues"]:
            data["timeline_comment"]["comment"] = data["timeline_comment"]["comment"] + attribute["Attribute"] + ": " + attribute["Value"] + "\n"
    return data


def run_cron_import():
    config = get_settings("external/hausfrage")
    print("import leads hausfrage")
    if config is None:
        print("no config for hausfrage import")
        return None

    import_time = datetime.now()
    if "last_lead_import_time" in config:
        leads = post("/Applications/Leads.ashx", parameters={
            "Action": "ACTION_PICKUP_LEADS",
            "Start": str(config["last_lead_import_time"]),
            "End": str(import_time)
        })
    else:
        leads = post("/Applications/Leads.ashx", parameters={
            "Action": "ACTION_PICKUP_LEADS",
            "Start": "2020-11-01 00:00:00",
            "End": str(import_time)
        })

    if leads is not None:
        for lead in leads:
            log = find_log("Lead", identifier=lead["Email"])
            if log is not None:
                print("already imported:", lead["Email"])
                continue

            data = get_import_data(lead)
            existing_contact = get_contact_by_email(lead["Email"])
            if existing_contact is None:
                data["lead"]["status_id"] = "NEW"
                contact = add_contact(data["contact"])
                if contact is not False:
                    data["lead"]["contact_id"] = contact["id"]
                else:
                    print(json.dumps(data["contact"], indent=2))

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
            log_item("Lead", lead["Email"])
        config = get_settings("external/hausfrage")
        if config is not None:
            config["last_lead_import_time"] = str(import_time)
        set_settings("external/hausfrage", config)
