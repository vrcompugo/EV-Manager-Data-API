import pprint
import json
from datetime import datetime, timedelta

from app import db
from app.models import Lead, Reseller, Customer
from app.utils.error_handler import error_handler
from app.modules.settings.settings_services import get_one_item as get_config_item, update_item as update_config_item
from app.modules.order.order_services import commission_calulation, add_item, update_item
from app.modules.reseller.services.reseller_services import update_item as update_reseller
from app.modules.offer.services.offer_generation.enpal_offer import enpal_offer_by_order

from ._connector import post, get
from ._association import find_association, associate_item
from ._field_values import convert_field_value_from_remote, convert_field_value_to_remote, convert_field_euro_from_remote
from .customer import run_import as customer_import


pp = pprint.PrettyPrinter()

CATEGORY_TYPES = {
    "FastUmsatzdarstellung": "salesstats",
    "Provision": "salesstats",
    "Verbau Photovoltaik": "pv_construction",
    "Verbau Heizung": "heating_construction",
    "Verbau BWWP": "pv_construction",
    "Verbau Dachsanierung": "roof_construction",
    "Verbau Dach/PV": "pv_roof_construction",
    "Verbau Elektrik": "electric_construction"
}


def filter_import_input(item_data):
    response = post("crm.dealcategory.get", {"ID": item_data["CATEGORY_ID"]})
    category = ""
    if "result" in response and "NAME" in response["result"]:
        category = response["result"]["NAME"]
    order_type = category
    if category in CATEGORY_TYPES:
        order_type = CATEGORY_TYPES[category]

    street = item_data["UF_CRM_1572962429"] if "UF_CRM_1572962429" in item_data else None
    street = street if street != "siehe Kundenanschrift" else None
    street_nb = item_data["UF_CRM_1572962442"] if "UF_CRM_1572962442" in item_data else None
    street_nb = street_nb if street_nb != "siehe Kundenanschrift" else None
    zip_code = item_data["UF_CRM_1572962458"] if "UF_CRM_1572962458" in item_data else None
    zip_code = zip_code if zip_code != "siehe Kundenanschrift" else None
    city = item_data["UF_CRM_1572962413"] if "UF_CRM_1572962413" in item_data else None
    city = city if city != "siehe Kundenanschrift" else None
    data = {
        "datetime": item_data["DATE_CREATE"],
        "label": item_data["TITLE"],
        "customer_id": None,
        "value_net": convert_field_euro_from_remote("UF_CRM_5DF8B018B26AF", item_data),
        "last_update": item_data["DATE_MODIFY"],
        "contact_source": convert_field_value_from_remote("SOURCE_ID", item_data),
        "status": "won",
        "type": order_type,
        "category": category,
        "street": street,
        "street_nb": street_nb,
        "zip": zip_code,
        "city": city,
        "commissions": None,
        "commission_value_net": 0,
        "data": {}
    }
    if "UF_CRM_1587030744" in item_data:
        data["data"]["usage_without_pv"] = convert_field_value_from_remote("UF_CRM_1587030744", item_data)
    if "UF_CRM_1587030804" in item_data:
        data["data"]["pv_size"] = convert_field_value_from_remote("UF_CRM_1587030804", item_data)
    if "UF_CRM_1587121259" in item_data:
        data["data"]["pdf_link"] = item_data["UF_CRM_1587121259"]

    if item_data["LEAD_ID"] is not None:
        link = find_association("Lead", remote_id=item_data["LEAD_ID"])
        if link is not None:
            data["lead_id"] = link.local_id
    if item_data["CONTACT_ID"] is not None:
        link = find_association("Customer", remote_id=item_data["CONTACT_ID"])
        if link is None:
            customer_import(remote_id=item_data["CONTACT_ID"])
            link = find_association("Customer", remote_id=item_data["CONTACT_ID"])
        if link is not None:
            data["customer_id"] = link.local_id
            customer = Customer.query.filter(Customer.id == link.local_id).first()
            if customer is not None and customer.default_address is not None:
                if data["street"] is None:
                    data["street"] = customer.default_address.street
                    data["street_nb"] = customer.default_address.street_nb
                if data["zip"] is None:
                    data["zip"] = customer.default_address.zip
                    data["city"] = customer.default_address.city
    if item_data["ASSIGNED_BY_ID"] is not None:
        link = find_association("Reseller", remote_id=item_data["ASSIGNED_BY_ID"])
        if link is not None:
            data["reseller_id"] = link.local_id
    value_pv = convert_field_euro_from_remote("UF_CRM_5DF8B018B26AF", item_data)
    discount_range = convert_field_value_from_remote("UF_CRM_5DF8B0188EF78", item_data)
    seperate_offer = convert_field_value_from_remote("UF_CRM_5DF8B018DA5E6", item_data)
    payment_type = convert_field_value_from_remote("UF_CRM_5DF8B018E971A", item_data)
    if data["type"] == "salesstats":
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
    print("order ", remote_id)
    response = post("crm.deal.get", {
        "ID": remote_id
    })
    if "result" in response:
        deal = response["result"]
        data = filter_import_input(deal)
        link = find_association("Order", remote_id=deal["ID"])
        if link is None:
            print("new order", deal["ID"])
            order = add_item(data)
            associate_item("Order", local_id=order.id, remote_id=deal["ID"])
            if order.type == "salesstats" and order.reseller_id is not None and order.reseller_id > 0:
                reseller = db.session.query(Reseller).filter(Reseller.id == order.reseller_id).first()
                if reseller is not None:
                    if reseller.lead_balance is None:
                        lead_balance = 0
                    else:
                        lead_balance = reseller.lead_balance
                    update_reseller(reseller.id, {"lead_balance": lead_balance + 8})
        else:
            print("update order", deal["ID"])
            order = update_item(link.local_id, data)
        if order is not None:
            if order.type == "salesstats":
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
                    return order
            return order
        return None
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
    from app.modules.offer.services.offer_generation import generate_offer_by_order
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
        deals2 = post("crm.deal.list", {
            "FILTER[>DATE_MODIFY]": config["data"]["last_order_import_datetime"],
            "FILTER[CATEGORY_ID]": 124
        })
    else:
        deals = post("crm.deal.list", {
            "FILTER[CATEGORY_ID]": 66
        })
        deals2 = post("crm.deal.list", {
            "FILTER[CATEGORY_ID]": 124
        })

    last_import = str(datetime.now())

    if "result" in deals:
        for deal in deals["result"]:
            try:
                order = run_import(remote_id=deal["ID"])
            except Exception as e:
                error_handler()

    if "result" in deals2:
        for deal in deals2["result"]:
            try:
                order = run_import(remote_id=deal["ID"])
                if order is not None and order.category == "online Speichernachrüstung" and ("pdf_link" not in order.data or order.data["pdf_link"] == ""):
                    generate_offer_by_order(order)

            except Exception as e:
                error_handler()

    config = get_config_item("importer/bitrix24")
    if config is not None and "data" in config:
        config["data"]["last_order_import_datetime"] = last_import
    update_config_item("importer/bitrix24", config)


def run_offer_pdf_export(local_id=None, remote_id=None, public_link=None):
    if local_id is not None:
        link = find_association("Order", local_id=local_id)
    if remote_id is not None:
        link = find_association("Order", remote_id=remote_id)
    if link is not None:
        response = post("crm.deal.update", {
            "id": link.remote_id,
            "fields[UF_CRM_1587121259]": public_link
        })
        print("offer pdf link resp:", response)
