import json
from app.modules.settings import get_settings

from ._connector import get, post
from ._field_values import flatten_dict


def convert_config_values(data_raw):
    config = get_settings(section="external/bitrix24")
    data = {}
    for key in data_raw.keys():
        if key[:2] == "UF":
            data[key] = data_raw[key]
        else:
            data[key.lower()] = data_raw[key]
    for local_field, external_field in config["company"]["fields"].items():
        if external_field.lower() in data:
            data[local_field] = data[external_field.lower()]
        if external_field in data:
            data[local_field] = data[external_field]
    return data


def get_company(id):
    config = get_settings(section="external/bitrix24")
    data = post("crm.company.get", {
        "ID": id
    })

    if "result" in data and len(data["result"]) > 0:
        return convert_config_values(data["result"])
    else:
        print("error get company:", data)
    return None


def get_company_contacts(id):
    config = get_settings(section="external/bitrix24")
    data = post("crm.company.contact.items.get", {
        "ID": id
    })

    if "result" in data and len(data["result"]) > 0:
        return data["result"]
    else:
        print("error get company:", data)
    return None


def add_company(data, domain=None):
    config = get_settings(section="external/bitrix24")
    fields = config["company"]["fields"]
    update_data = {}
    update_data = flatten_dict(data, update_data, fields=fields, config=config)
    response = post("crm.company.add", update_data, domain=domain)
    if "result" in response and response["result"]:
        return get_company(int(response["result"]))
    else:
        return False


def update_company(id, data, domain=None):
    update_data = {"id": id}
    config = get_settings(section="external/bitrix24", domain_raw=domain)
    fields = config["company"]["fields"]
    update_data = flatten_dict(data, update_data, fields=fields, config=config)
    response = post("crm.company.update", update_data, domain=domain)
    if "result" in response and response["result"]:
        return response["result"]
    else:
        return False
