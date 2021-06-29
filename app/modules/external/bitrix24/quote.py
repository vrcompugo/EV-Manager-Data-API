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
    for local_field, external_field in config["quote"]["fields"].items():
        if external_field.lower() in data:
            data[local_field] = data[external_field.lower()]
        if external_field in data:
            data[local_field] = data[external_field]
    data["opportunity"] = float(data["opportunity"])
    data["tax_value"] = float(data["tax_value"])
    data["company"] = None
    data["contact"] = {}
    if "contact_id" in data and data["contact_id"] is not None and data["contact_id"] is not False and data["contact_id"] != "" and int(data["contact_id"]) > 0:
        contact_data = get_contact(data["contact_id"])
        if contact_data is not None:
            data["email"] = contact_data["email"]
            data["contact"] = {
                "salutation": contact_data["salutation"],
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
            data["name"] = contact_data["first_name"]
            data["first_name"] = contact_data["first_name"]
            data["last_name"] = contact_data["last_name"]
            data["firstname"] = contact_data["first_name"]
            data["lastname"] = contact_data["last_name"]

    return data


def get_quote(id):
    data = post("crm.quote.get", {
        "ID": id
    })
    if "result" in data:
        return convert_config_values(data["result"])
    else:
        print("error get quote:", data)
    return None


def get_quote_products(id):
    data = post("crm.quote.productrows.get", {
        "id": id
    })
    if "result" in data:
        return data["result"]
    else:
        print("error:", data)
    return None


def update_quote_products(id, data, domain=None):
    if "products" not in data:
        return False
    config = get_settings(section="external/bitrix24")
    index = 0
    update_data = {"id": id}
    for product in data["products"]:
        if "PRICE" not in product:
            print(product)
            continue
        if product["quantity"] <= 0:
            continue
        product_data = {
            "PRODUCT_NAME": product["NAME"],
            "ORIGINAL_PRODUCT_NAME": product["NAME"],
            "PRODUCT_DESCRIPTION": product["DESCRIPTION"],
            "PRICE": product["PRICE"],
            "PRICE_EXCLUSIVE": product["PRICE"],
            "PRICE_NETTO": product["PRICE"],
            "PRICE_BRUTTO": product["PRICE"],
            "PRICE_ACCOUNT": product["PRICE"],
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
        if "MEASURE" in product:
            unit = next((key for key in config["quote"]["units"].keys() if config["quote"]["units"][key] == str(product["quantity_unit"])), None)
            if unit is not None:
                product_data["MEASURE_CODE"] = unit
            else:
                product_data["MEASURE_CODE"] = product["MEASURE"]
        if "quantity_unit" in product:
            product_data["MEASURE_NAME"] = product["quantity_unit"]
        if "ID" in product:
            product_data["PRODUCT_ID"] = product["ID"]
        for key in product_data.keys():
            update_data[f"rows[{index}][{key.upper()}]"] = product_data[key]
        index = index + 1
    response = post("crm.quote.productrows.set", update_data, domain=domain)
    if "result" in response and response["result"]:
        return True
    else:
        return False


def add_quote(data, domain=None):
    config = get_settings(section="external/bitrix24", domain_raw=domain)
    fields = config["quote"]["fields"]
    update_data = {}
    update_data = flatten_dict(data, update_data, fields=fields, config=config)
    response = post("crm.quote.add", update_data, domain=domain)
    if "result" in response and response["result"]:
        return get_quote(int(response["result"]))
    else:
        return False


def update_quote(id, data, domain=None):
    update_data = {"id": id}
    config = get_settings(section="external/bitrix24", domain_raw=domain)
    fields = config["quote"]["fields"]
    update_data = flatten_dict(data, update_data, fields=fields, config=config)
    response = post("crm.quote.update", update_data, domain=domain)
    if "result" in response and response["result"]:
        return True
    else:
        return False
