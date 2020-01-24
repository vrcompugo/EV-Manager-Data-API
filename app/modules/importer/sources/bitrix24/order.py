import pprint
from datetime import datetime, timedelta

from app import db
from app.models import Lead
from app.utils.error_handler import error_handler
from app.modules.settings.settings_services import get_one_item as get_config_item, update_item as update_config_item
from app.modules.lead.lead_services import lead_commission_calulation, update_item

from ._connector import post, get
from ._association import find_association, associate_item
from ._field_values import convert_field_value_from_remote, convert_field_value_to_remote, convert_field_euro_from_remote


pp = pprint.PrettyPrinter()


def run_import(local_id=None, remote_id=None):
    if remote_id is not None:
        response = post("crm.deal.get", {
            "ID": remote_id
        })
        if "result" in response:
            deal = response["result"]
            link = find_association("Lead", remote_id=deal["LEAD_ID"])
            if link is not None:
                lead = db.session.query(Lead).get(link.local_id)
                value_pv = convert_field_euro_from_remote("UF_CRM_5DF8B018B26AF", deal)
                discount_range = convert_field_value_from_remote("UF_CRM_5DF8B0188EF78", deal)
                seperate_offer = convert_field_value_from_remote("UF_CRM_5DF8B018DA5E6", deal)
                payment_type = convert_field_value_from_remote("UF_CRM_5DF8B018E971A", deal)
                pv_commission = {
                    "type": "PV",
                    "value_net": value_pv,
                    "discount_range": discount_range,
                    "options": [],
                    "provision_rate": None,
                    "provision_net": None,
                    "payment_type": payment_type
                }
                if seperate_offer == "Wärmepumpe (ecoStar) verkauft":
                    pv_commission["options"].append({
                        "key": "Wärmepumpe (ecoStar)",
                        "value_net": None
                    })
                lead.commissions = [
                    pv_commission
                ]
                print("update commission data lead ", lead.id)
                db.session.commit()
                return lead
            else:
                print("no local lead")
        else:
            pp.pprint(response)
    return None


def run_import_by_lead(lead: Lead):
    if lead.status == "won":
        link = find_association("Lead", local_id=lead.id)
        if link is not None:
            response = post("crm.deal.list", {
                "FILTER[LEAD_ID]": link.remote_id,
                "FILTER[CATEGORY_ID]": 66
            })
            pp.pprint(response)
            if "result" in response and len(response["result"]) > 0:
                lead_new = run_import(remote_id=response["result"][0]["ID"])
                if lead_new is not None:
                    return lead_new
    return lead


def run_cron_import():
    try:
        config = get_config_item("importer/bitrix24")
        print("import order data bitrix24 ")
        if config is None:
            print("no config for bitrix import")
            return None
        if "data" in config and "last_order_import_datetime" in config["data"]:
            deals = post("crm.deal.list", {
                "FILTER[>DATE_MODIFY]": config["data"]["last_order_import_datetime"],
                "FILTER[CATEGORY_ID]": 66
            })
        else:
            deals = post("crm.deal.list", {
                "FILTER[CATEGORY_ID]": 66
            })

        if "result" in deals:
            for deal in deals["result"]:
                lead = run_import(remote_id=deal["ID"])
                if lead is not None:
                    lead = update_item(lead.id, {"commissions": lead.commissions})
                    commissions = lead_commission_calulation(lead).commissions
                    update_item(lead.id, {"commissions": None})
                    lead = update_item(lead.id, {"commissions": commissions})
                    print(lead.commissions)

            config = get_config_item("importer/bitrix24")
            if config is not None and "data" in config:
                config["data"]["last_order_import_datetime"] = datetime.now()
            update_config_item("importer/bitrix24", config)
    except Exception as e:
        error_handler()
