import pprint
import json
import requests
import base64
from datetime import datetime, timedelta

from app import db
from app.models import Lead, Reseller, Customer, Order
from app.utils.error_handler import error_handler
from app.modules.settings.settings_services import get_one_item as get_config_item, update_item as update_config_item, get_settings
from app.modules.order.order_services import commission_calulation, add_item, update_item
from app.modules.reseller.services.reseller_services import update_item as update_reseller
from app.modules.offer.services.offer_generation.enpal_offer import enpal_offer_by_order
from app.modules.external.bitrix24.drive import get_file_content

from ._connector import post, get
from ._association import find_association, associate_item
from ._field_values import convert_field_value_from_remote, convert_field_value_to_remote, convert_field_euro_from_remote, convert_data_to_post_data
from .customer import run_import as customer_import
from .drive import get_file


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
    config = get_settings("external/bitrix24")
    response = post("crm.dealcategory.get", {"ID": item_data["CATEGORY_ID"]})
    category = ""
    if "result" in response and "NAME" in response["result"]:
        category = response["result"]["NAME"]
    order_type = ""
    if category in CATEGORY_TYPES:
        order_type = CATEGORY_TYPES[category]

    street = item_data["UF_CRM_1572962429"] if "UF_CRM_1572962429" in item_data else None
    street = street if street != "siehe Kundenanschrift" else None
    if street is None or street == "":
        street = item_data["UF_CRM_5DD4F51D40C8D"] if "UF_CRM_5DD4F51D40C8D" in item_data else None
    street_nb = item_data["UF_CRM_1572962442"] if "UF_CRM_1572962442" in item_data else None
    street_nb = street_nb if street_nb != "siehe Kundenanschrift" else None
    if street_nb is None or street_nb == "":
        street_nb = item_data["UF_CRM_5DD4F51D4CA3E"] if "UF_CRM_5DD4F51D4CA3E" in item_data else None
    zip_code = item_data["UF_CRM_1572962458"] if "UF_CRM_1572962458" in item_data else None
    zip_code = zip_code if zip_code != "siehe Kundenanschrift" else None
    if zip_code is None or zip_code == "":
        zip_code = item_data["UF_CRM_5DD4F51D603E2"] if "UF_CRM_5DD4F51D603E2" in item_data else None
    city = item_data["UF_CRM_1572962413"] if "UF_CRM_1572962413" in item_data else None
    city = city if city != "siehe Kundenanschrift" else None
    if city is None or city == "":
        city = item_data["UF_CRM_5DD4F51D57898"] if "UF_CRM_5DD4F51D57898" in item_data else None
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
        "data": item_data
    }
    if "UF_CRM_1587030744" in item_data:
        data["data"]["usage_without_pv"] = convert_field_value_from_remote("UF_CRM_1587030744", item_data)
    if config["deal"]["fields"]["contract_number"] in item_data:
        data["contract_number"] = item_data[config["deal"]["fields"]["contract_number"]]
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


def filter_export_input(order: Order):
    data = filter_export_input_all(order)
    data = filter_export_input_cloud(data, order)
    return convert_data_to_post_data(data, "deal")


def filter_export_input_all(order: Order):
    from .customer import run_export as run_customer_export

    if order.category != "Cloud Verträge":
        return None
    config = get_settings("external/bitrix24")
    data = {
        "TITLE": order.label,
        "TYPE_ID": "SALE",
        "STAGE_ID": convert_field_value_to_remote("status", order.__dict__),
        "CURRENCY_ID": "EUR",
        "OPPORTUNITY": float(order.value_net),
        "BEGINDATE": str(order.datetime),
        "DATE_CREATE": str(order.datetime),
        "OPENED": "Y",
        "CLOSED": "N",
        "CATEGORY_ID": convert_field_value_to_remote("category", order.__dict__),
        "SOURCE_ID": convert_field_value_to_remote("contact_source", order.__dict__),
        "contract_number": order.contract_number
    }

    customer_link = find_association("Customer", local_id=order.customer_id)
    if customer_link is None:
        run_customer_export(local_id=order.customer_id)
        customer_link = find_association("Customer", local_id=order.customer_id)
    if customer_link is not None:
        data['CONTACT_ID'] = customer_link.remote_id
    customer_company_link = find_association("CustomerCompany", local_id=order.customer_id)
    if customer_company_link is not None:
        data['COMPANY_ID'] = customer_company_link.remote_id
    return data


def filter_export_input_cloud(data, order: Order, consumer_index=None):
    if order.category != "Cloud Verträge":
        return data
    data["has_consumer"] = False
    data["is_consumer"] = False
    data["has_ecloud"] = False
    if consumer_index is None:
        if "consumers" in order.data and len(order.data["consumers"]) > 0:
            data["has_consumer"] = True
        if "ecloud_usage" in order.data and order.data["ecloud_usage"] != "" and order.data["ecloud_usage"] is not None and int(order.data["ecloud_usage"]) > 0:
            data["has_ecloud"] = True
        data["emove_tarif"] = None
        data["cloud_files"] = []
        data["TITLE"] = f"{order.contract_number} {order.label} | Cloud {order.contact_source}"
        for field in ["company", "firstname", "lastname", "street", "street_nb", "city", "zip"]:
            if field in order.data["address"]:
                data[field.upper()] = order.data["address"][field]
        for field in ["power_meter_number", "power_usage", "heatcloud_power_meter_number", "heater_usage",
                      "emove_tarif", "price_guarantee", "offer_number", "construction_date", "smartme_number",
                      "bankowner", "iban", "bic", "malo_lightcloud", "malo_heatcloud", "malo_ecloud", "malo_consumer1", "malo_consumer2", "malo_consumer3"]:
            if field in order.data:
                if field == "power_usage":
                    data["USAGE"] = int(order.data[field])
                if field == "heater_usage" and "USAGE" in data and order.data[field] != "":
                    data["USAGE"] = int(data["USAGE"]) + int(order.data[field])
                if field == "price_guarantee":
                    if order.data[field] is not None and order.data[field] != "":
                        data[field.upper()] = int(order.data[field].replace("_years", ""))
                else:
                    data[field.upper()] = order.data[field]
                    data[field] = order.data[field]

        for file_key in ["cloud_config_id", "signed_offer_pdf_id", "refund_transfer_pdf_id", "sepa_form_id",
                         "old_power_invoice_id", "old_gas_invoice_id"]:
            if file_key in order.data:
                file = get_file(order.data[file_key])
                file_content = get_file_content(order.data[file_key])
                data["cloud_files"].append({
                    "fileData": [
                        file["NAME"],
                        base64.encodestring(file_content).decode("utf-8")
                    ]
                })
        if order.offer is not None and order.offer.pdf is not None:
            r = order.offer.pdf.get_file()
            if r is not None:
                content = r.read()
                data["cloud_configuration_file"] = [
                    "Cloud Konfiguration.pdf",
                    base64.encodestring(content).decode("utf-8")
                ]
            data["cloud_configuration_file_link"] = order.offer.pdf.longterm_public_link
    else:
        consumer = order.data["consumers"][consumer_index]
        consumer_data = data
        consumer_data["TITLE"] = f"{order.contract_number}c{consumer_index + 1} {order.label} | Cloud {order.contact_source}"
        consumer_data["contract_number"] = f"{order.contract_number}c{consumer_index + 1}"
        consumer_data["has_consumer"] = False
        consumer_data["is_consumer"] = True
        for field in ["company", "firstname", "lastname", "street", "street_nb", "city", "zip"]:
            if field in consumer["address"]:
                consumer_data[field.upper()] = consumer["address"][field]
        for field in ["power_meter_number", "usage"]:
            if field in consumer:
                if field == "usage":
                    consumer_data["POWER_USAGE"] = consumer[field]
                consumer_data[field.upper()] = consumer[field]
        consumer_data["offer_number".upper()] = order.data["offer_number"]
        return consumer_data
    return data


def filter_export_input_ecloud(data, order: Order):
    if order.category != "Cloud Verträge":
        return data
    data["has_consumer"] = False
    data["is_consumer"] = False
    data["has_ecloud"] = False
    data["TITLE"] = f"{order.contract_number}E {order.label} | Cloud {order.contact_source}"
    data["contract_number"] = f"{order.contract_number}E"
    data["has_consumer"] = False
    data["is_consumer"] = False
    data["CATEGORY_ID"] = 140
    data["STAGE_ID"] = "C140:NEW"
    for field in ["company", "firstname", "lastname", "street", "street_nb", "city", "zip"]:
        if field in order.data["address"]:
            data[field.upper()] = order.data["address"][field]
    data["power_meter_number".upper()] = order.data["power_meter_number"]
    data["usage".upper()] = order.data["ecloud_usage"]
    data["power_usage".upper()] = 0
    data["offer_number".upper()] = order.data["offer_number"]
    return data


def run_export(local_id=None, remote_id=None):
    if local_id is not None:
        link = find_association("Order", local_id=local_id)
        order = Order.query.get(local_id)
    if remote_id is not None:
        link = find_association("Order", remote_id=remote_id)
        order = Order.query.get(link.local_id)
    post_data = filter_export_input_all(order)
    consumer_data_base = json.loads(json.dumps(post_data))
    post_data = filter_export_input_cloud(post_data, order)
    post_data2 = convert_data_to_post_data(post_data, "deal")
    if link is None:
        print("run export order new")
        response = post("crm.deal.add", convert_data_to_post_data(post_data, "deal"))
        if "result" in response:
            associate_item("Order", local_id=local_id, remote_id=response["result"])
        else:
            print("error export", response)
    else:
        print("run export order update", link.remote_id)
        post_data["id"] = link.remote_id
        response = post("crm.deal.update", convert_data_to_post_data(post_data, "deal"))
        if "result" in response:
            print("error export update", response)
    # if "consumers" in order.data:
    #     for i, consumer in enumerate(order.data["consumers"]):
    #         link = find_association(f"OrderC{i}", local_id=local_id)
    #         post_data = filter_export_input_cloud(consumer_data_base, order, consumer_index=i)
    #        if link is None:
    #            response = post("crm.deal.add", convert_data_to_post_data(post_data, "deal"))
    #            if "result" in response:
    #                associate_item(f"OrderC{i}", local_id=local_id, remote_id=response["result"])
    #        else:
    #            post_data["id"] = link.remote_id
    #            response = post("crm.deal.update", convert_data_to_post_data(post_data, "deal"))
    #if "ecloud_usage" in order.data and order.data["ecloud_usage"] != "" and order.data["ecloud_usage"] is not None and int(order.data["ecloud_usage"]) > 0:
    #    link = find_association("OrderECloud", local_id=local_id)
    #    post_data = filter_export_input_ecloud(consumer_data_base, order)
    #    if link is None:
    #        response = post("crm.deal.add", convert_data_to_post_data(post_data, "deal"))
    #        if "result" in response:
    #            associate_item("OrderECloud", local_id=local_id, remote_id=response["result"])
    #    else:
    #        post_data["id"] = link.remote_id
    #        response = post("crm.deal.update", convert_data_to_post_data(post_data, "deal"))


def run_export_fields(local_id=None, remote_id=None, fields=[]):
    if local_id is not None:
        link = find_association("Order", local_id=local_id)
        order = Order.query.get(local_id)
    if remote_id is not None:
        link = find_association("Order", remote_id=remote_id)
        order = Order.query.get(link.local_id)
    if link is None:
        return None

    config = get_settings("external/bitrix24")
    post_data = {}
    for field in fields:
        if hasattr(order, field):
            post_data[field] = getattr(order, field)
    if len(post_data) > 0:
        post_data["id"] = link.remote_id
        response = post("crm.deal.update", convert_data_to_post_data(post_data, "deal"))
        if "result" in response:
            return order
    return None
