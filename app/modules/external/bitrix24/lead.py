import json

from app.modules.settings import get_settings
from app.modules.external.bitrix24.contact import get_contact
from app.modules.external.bitrix24.user import get_user
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
        if external_field in data:
            data[local_field] = data[external_field]

    return data


def get_lead(id):
    data = post("crm.lead.get", {
        "ID": id
    })
    if "result" in data:
        return convert_config_values(data["result"])
    else:
        print("error:", data)
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
    update_data = flatten_dict(data, update_data, fields=fields, config=config)
    response = post("crm.lead.add", update_data, domain=domain)
    if "result" in response and response["result"]:
        return get_deal(int(response["result"]))
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