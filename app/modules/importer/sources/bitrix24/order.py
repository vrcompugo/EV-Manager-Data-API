import pprint
import json
from datetime import datetime, timedelta

from app import db
from app.models import Lead
from app.utils.error_handler import error_handler
from app.modules.settings.settings_services import get_one_item as get_config_item, update_item as update_config_item
from app.modules.order.order_services import commission_calulation, add_item, update_item

from ._connector import post, get
from ._association import find_association, associate_item
from ._field_values import convert_field_value_from_remote, convert_field_value_to_remote, convert_field_euro_from_remote


pp = pprint.PrettyPrinter()


def filter_import_input(item_data):
    data = {
        "datetime": item_data["DATE_CREATE"],
        "customer_id": None,
        "value_net": convert_field_euro_from_remote("UF_CRM_5DF8B018B26AF", item_data),
        "last_update": item_data["DATE_MODIFY"],
        "contact_source": convert_field_value_from_remote("SOURCE_ID", item_data),
        "status": "won",
        "commissions": None,
        "commission_value_net": 0
    }
    if item_data["LEAD_ID"] is not None:
        link = find_association("Lead", remote_id=item_data["LEAD_ID"])
        if link is not None:
            data["lead_id"] = link.local_id
    if item_data["CONTACT_ID"] is not None:
        link = find_association("Customer", remote_id=item_data["CONTACT_ID"])
        if link is not None:
            data["customer_id"] = link.local_id
    if item_data["ASSIGNED_BY_ID"] is not None:
        link = find_association("Reseller", remote_id=item_data["ASSIGNED_BY_ID"])
        if link is not None:
            data["reseller_id"] = link.local_id
    value_pv = convert_field_euro_from_remote("UF_CRM_5DF8B018B26AF", item_data)
    discount_range = convert_field_value_from_remote("UF_CRM_5DF8B0188EF78", item_data)
    seperate_offer = convert_field_value_from_remote("UF_CRM_5DF8B018DA5E6", item_data)
    payment_type = convert_field_value_from_remote("UF_CRM_5DF8B018E971A", item_data)
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
    data["commissions"] = [
        pv_commission
    ]
    return data


def run_import(local_id=None, remote_id=None):
    if local_id is not None:
        link = find_association("Order", local_id=local_id)
        if link is not None:
            remote_id = link.remote_id
    if remote_id is None:
        print("no id given")
        return None
    response = post("crm.deal.get", {
        "ID": remote_id
    })
    if "result" in response:
        deal = response["result"]
        data = filter_import_input(deal)
        pp.pprint(deal)
        pp.pprint(data)
        link = find_association("Order", remote_id=deal["ID"])
        if link is None:
            order = add_item(data)
            associate_item("Order", local_id=order.id, remote_id=deal["ID"])
        else:
            order = update_item(link.local_id, data)
        if order is not None:
            order = commission_calulation(order)
            if order is not None:
                commissions = json.loads(json.dumps(order.commissions))
                update_item(order.id, {
                    "commissions": None,
                    "commission_value_net": order.commission_value_net,
                })
                update_item(order.id, {
                    "commissions": commissions
                })
        return
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
                order = run_import(remote_id=response["result"][0]["ID"])
                if order is not None:
                    return order
    return None


def run_cron_import():
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
            try:
                order = run_import(remote_id=deal["ID"])
            except Exception as e:
                error_handler()

        config = get_config_item("importer/bitrix24")
        if config is not None and "data" in config:
            config["data"]["last_order_import_datetime"] = str(datetime.now())
        update_config_item("importer/bitrix24", config)
