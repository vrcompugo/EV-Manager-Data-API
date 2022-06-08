from datetime import datetime
import json

from app.modules.settings import get_settings, set_settings
from app.modules.external.bitrix24.contact import get_contact
from app.modules.external.bitrix24.user import get_user
from app.modules.external.bitrix24.deal import add_deal, get_deals, update_deal
from app.utils.dict_func import flatten_dict

from ._connector import get, post
from ._field_values import convert_field_euro_from_remote, convert_field_select_from_remote


def convert_config_values(data_raw):
    config = get_settings(section="external/bitrix24")
    data = {}
    for key in data_raw.keys():
        if key[:2] == "UF":
            data[key] = data_raw[key]
        else:
            data[key.lower()] = data_raw[key]
    for local_field, external_field in config["lead"]["fields"].items():
        if external_field.lower() in data:
            data[local_field] = data[external_field.lower()]
        if external_field in data:
            data[local_field] = data[external_field]
    data["company"] = data["company_title"]
    data["contact"] = {
        "company": data["company_title"],
        "name": data["first_name"],
        "first_name": data["first_name"],
        "last_name": data["last_name"],
        "firstname": data["first_name"],
        "lastname": data["last_name"],
        "street": data.get("street"),
        "street_nb": data.get("street_nb"),
        "zip": data.get("zip"),
        "city": data.get("city")
    }
    if "contact_id" in data and data["contact_id"] is not None and data["contact_id"] is not False and data["contact_id"] != "" and int(data["contact_id"]) > 0:
        contact_data = get_contact(data["contact_id"])
        if contact_data is not None:
            data["contact"] = {
                "name": contact_data["first_name"],
                "first_name": contact_data["first_name"],
                "last_name": contact_data["last_name"],
                "firstname": contact_data["first_name"],
                "lastname": contact_data["last_name"],
                "street": contact_data["street"],
                "street_nb": contact_data["street_nb"],
                "zip": contact_data["zip"],
                "city": contact_data["city"]
            }
            if "email" in contact_data:
                data["email"] = contact_data["email"]
                data["contact"]["email"] = contact_data["email"]
            if "phone" in contact_data:
                data["phone"] = contact_data["phone"]
                data["contact"]["phone"] = contact_data["phone"]
            data["name"] = contact_data["first_name"]
            data["first_name"] = contact_data["first_name"]
            data["last_name"] = contact_data["last_name"]
            data["firstname"] = contact_data["first_name"]
            data["lastname"] = contact_data["last_name"]

    return data


def get_lead(id, force_reload=False):
    data = post("crm.lead.get", {
        "ID": id
    }, force_reload=force_reload)
    if "result" in data:
        return convert_config_values(data["result"])
    else:
        print("error get lead:", data)
    return None


def get_lead_products(id):
    data = post("crm.lead.productrows.get", {
        "id": id
    })
    if "result" in data:
        return data["result"]
    else:
        print("error:", data)
    return None


def update_lead_products(id, data, domain=None):
    if "products" not in data:
        return False
    config = get_settings(section="external/bitrix24")
    index = 0
    update_data = {"id": id}
    for product in data["products"]:
        if "price" not in product:
            print(product)
            continue
        product_data = {
            "PRODUCT_NAME": product["label"],
            "ORIGINAL_PRODUCT_NAME": product["label"],
            "PRODUCT_DESCRIPTION": product["description"],
            "PRICE": product["price"],
            "PRICE_EXCLUSIVE": product["price"],
            "PRICE_NETTO": product["price"],
            "PRICE_BRUTTO": product["price"],
            "PRICE_ACCOUNT": product["price"],
            "QUANTITY": product["quantity"],
            "DISCOUNT_TYPE_ID": 2,
            "DISCOUNT_RATE": 0,
            "DISCOUNT_SUM": 0,
            "TAX_RATE": config["taxrate"],
            "TAX_INCLUDED": "N",
            "CUSTOMIZED": "Y",
            "MEASURE_CODE": 796,
            "MEASURE_NAME": "Stück",
            "SORT": 10
        }
        if "id" in product:
            product_data["PRODUCT_ID"] = product["id"]
        for key in product_data.keys():
            update_data[f"rows[{index}][{key.upper()}]"] = product_data[key]
        index = index + 1
    response = post("crm.lead.productrows.set", update_data, domain=domain)
    if "result" in response and response["result"]:
        return True
    else:
        return False


def add_lead(data, domain=None):
    config = get_settings(section="external/bitrix24", domain_raw=domain)
    fields = config["lead"]["fields"]
    update_data = {}
    data = set_address_if_empty(data)
    update_data = flatten_dict(data, update_data, fields=fields, config=config)
    response = post("crm.lead.add", update_data, domain=domain)
    if "result" in response and response["result"]:
        return get_lead(int(response["result"]), force_reload=True)
    else:
        return False


def update_lead(id, data, domain=None):
    update_data = {"id": id}
    config = get_settings(section="external/bitrix24", domain_raw=domain)
    fields = config["lead"]["fields"]
    update_data = flatten_dict(data, update_data, fields=fields, config=config)
    response = post("crm.lead.update", update_data, domain=domain)
    if "result" in response and response["result"]:
        return True
    else:
        return False


def set_address_if_empty(data):
    if "street" in data:
        if data["street"] is None or data["street"] is False or data["street"] == "":
            data["street"] = "siehe Kundenanschrift"
    if "street_nb" in data:
        if data["street_nb"] is None or data["street_nb"] is False or data["street_nb"] == "":
            data["street_nb"] = "siehe Kundenanschrift"
    if "zip" in data:
        if data["zip"] is None or data["zip"] is False or data["zip"] == "":
            data["zip"] = "siehe Kundenanschrift"
    if "city" in data:
        if data["city"] is None or data["city"] is False or data["city"] == "":
            data["city"] = "siehe Kundenanschrift"
    return data


def get_leads_by_createdate(created_after_datetime):
    payload = {
        "FILTER[>DATE_CREATE]": str(created_after_datetime),
        "start": 0
    }
    result = []
    while payload["start"] is not None:
        data = post("crm.lead.list", payload, force_reload=True)
        if "result" in data:
            payload["start"] = data["next"] if "next" in data else None
            for item in data["result"]:
                result.append(item)
        else:
            print("error3:", data)
            payload["start"] = None
            return None
    return result


def get_leads(payload):
    payload["start"] = 0
    result = []
    while payload["start"] is not None:
        data = post("crm.lead.list", payload)
        if "result" in data:
            payload["start"] = data["next"] if "next" in data else None
            for item in data["result"]:
                result.append(convert_config_values(item))
        else:
            print("error3:", data)
            payload["start"] = None
            return None
    return result


def convert_lead_to_deal(lead):
    return lead


def run_aev_lead_convert():
    config = get_settings("external/bitrix24/aev_lead_convert")
    print("aev_lead_convert")
    if config is None:
        print("no config for aev_lead_convert import")
        return None
    now = datetime.now()
    leads = get_leads({
        "FILTER[>DATE_CREATE]": config.get("last_import", "2021-01-01"),
        "FILTER[SOURCE_ID]": "23"
    })
    if leads is not None:
        for lead_data in leads:
            lead = get_lead(lead_data["id"])
            lead["unique_identifier"] = lead["id"]
            deal_datas = get_deals({
                "FILTER[UF_CRM_5FA43F983EBAB]": lead["unique_identifier"],
                "FILTER[CATEGORY_ID]": "170",
                "SELECT[0]": "ID",
                "SELECT[1]": "UF_CRM_5FA43F983EBAB"
            })
            if len(deal_datas) == 0:
                deal_data = convert_lead_to_deal(lead)
                deal_data["category_id"] = "170"
                add_deal(deal_data)
        config = get_settings("external/bitrix24/aev_lead_convert")
        if config is not None:
            config["last_import"] = now.astimezone().isoformat()
        set_settings("external/bitrix24/aev_lead_convert", config)


def run_bennemann_lead_convert():
    config = get_settings("external/bitrix24/bennemann_lead_convert")
    print("bennemann_lead_convert")
    if config is None:
        print("no config for bennemann_lead_convert import")
        return None
    now = datetime.now()
    deals = get_deals({
        "SELECT": "full",
        "FILTER[>CHANGED_DATE]": config.get("last_import", "2021-01-01"),
        "FILTER[CATEGORY_ID]": "180"
    }, force_reload=True)
    if deals is not None:
        for deal in deals:
            if deal.get("unique_identifier") in [None, "", "None", "0"]:
                contact = get_contact(deal.get("contact_id"))
                if contact is None or contact.get("email") in [None, ""] or len(contact.get("email")) == 0:
                    continue
                lead_data = deal
                lead_data["status_id"] = "16"
                lead = add_lead(deal)
                if lead is not None and "id" in lead:
                    update_deal(deal.get("id"), {
                        "unique_identifier": lead.get("id")
                    })
        config = get_settings("external/bitrix24/bennemann_lead_convert")
        if config is not None:
            config["last_import"] = now.astimezone().isoformat()
        set_settings("external/bitrix24/bennemann_lead_convert", config)