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

from ._connector import post, get
from ._association import log_item, find_log


def get_import_data(raw):
    street, street_nb = street_to_street_with_nb(raw["offer_contact"]["address"])
    data = {
        "contact": {
            "salutation": "ms" if raw["offer_contact"]["salutation"] == "Frau" else "mr",
            "title": "",
            "first_name": raw["offer_contact"]["first_name"],
            "last_name": raw["offer_contact"]["last_name"],
            "street": street,
            "street_nb": street_nb,
            "zip": raw["offer_contact"]["zip_code"],
            "city": raw["offer_contact"]["city"],
            "email": [
                {
                    "VALUE_TYPE": "WORK",
                    "VALUE": raw["offer_contact"]["email"],
                    "TYPE_ID": "EMAIL"
                }
            ],
            "phone": [
                {
                    "VALUE_TYPE": "WORK",
                    "VALUE": internationalize_phonenumber(raw["offer_contact"]["phone"]),
                    "TYPE_ID": "PHONE"
                }
            ]
        },
        "lead": {
            "title": f"{raw['offer_contact']['first_name']} {raw['offer_contact']['last_name']}, {raw['offer_contact']['city']} (Aroundhome)",
            "source_id": "16",
            "first_name": raw["offer_contact"]["first_name"],
            "last_name": raw["offer_contact"]["last_name"],
            "street": street,
            "street_nb": street_nb,
            "zip": raw["offer_contact"]["zip_code"],
            "city": raw["offer_contact"]["city"]
        },
        "timeline_comment": {
            "entity_type": "lead",
            "comment": ""
        }
    }
    if "company" in raw['offer_contact'] and raw['offer_contact']['company'] != "" and raw['offer_contact']['company'] != "Privatperson":
        data["company"] = {
            "company": raw['offer_contact']['company'],
            "street": street,
            "street_nb": street_nb,
            "zip": raw["offer_contact"]["zip_code"],
            "city": raw["offer_contact"]["city"],
            "email": [
                {
                    "VALUE_TYPE": "WORK",
                    "VALUE": raw["offer_contact"]["email"],
                    "TYPE_ID": "EMAIL"
                }
            ],
            "phone": [
                {
                    "VALUE_TYPE": "WORK",
                    "VALUE": raw["offer_contact"]["phone"],
                    "TYPE_ID": "PHONE"
                }
            ]
        }
    if raw['offer_contact']['address'] != raw['installation_contact']['address']:
        street2, street_nb2 = street_to_street_with_nb(raw["installation_contact"]["address"])
        data["lead"]["street"] = street2
        data["lead"]["street_nb"] = street_nb2
        data["lead"]["zip"] = raw["installation_contact"]["zip_code"]
        data["lead"]["city"] = raw["installation_contact"]["city"]

    if "product_name" in raw:
        data["timeline_comment"]["comment"] = data["timeline_comment"]["comment"] + "Produkt: " + raw["product_name"] + "\n"
    if "reachability" in raw:
        data["timeline_comment"]["comment"] = data["timeline_comment"]["comment"] + "Erreichbarkeit: " + raw["reachability"] + "\n"
    if "answered_questions" in raw:
        for item in raw["answered_questions"]:
            data["timeline_comment"]["comment"] = data["timeline_comment"]["comment"] \
                + item["question"] + " "
            for item2 in item["answers"]:
                data["timeline_comment"]["comment"] = data["timeline_comment"]["comment"] \
                    + item2["answer"] + ", "
            data["timeline_comment"]["comment"] = data["timeline_comment"]["comment"] + "\n"
    return data


def run_cron_import():
    config = get_settings("external/aroundhome")
    print("import leads aroundhome")
    if config is None:
        print("no config for aroundhome import")
        return None
    last_import = datetime(2020, 11, 1, 0, 0, 0)
    import_time = datetime.now()
    if "last_lead_import_time" in config:
        last_import = datetime.strptime(config["last_lead_import_time"], "%Y-%m-%d %H:%M:%S.%f")
    leads = get("/v201609/leads", parameters={
        "per_page": 10000,
        "from_timestamp": int(datetime.timestamp(last_import)),
    })

    if leads is not None:
        for lead in leads:
            log = find_log("Lead", identifier=lead["lead_id"])
            if log is not None:
                print("already imported:", lead["lead_id"])
                continue
            data = get_import_data(lead)
            existing_contact = get_contact_by_email(lead["offer_contact"]["email"])
            if existing_contact is None:
                data["lead"]["status_id"] = "NEW"
                contact = add_contact(data["contact"])
                if contact is not False:
                    data["lead"]["contact_id"] = contact["id"]

                if "company" in data:
                    if contact is not False:
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
            log_item("Lead", lead["lead_id"])
        config = get_settings("external/aroundhome")
        if config is not None:
            config["last_lead_import_time"] = str(import_time)
        set_settings("external/aroundhome", config)
