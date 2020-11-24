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
    for local_field, external_field in config["contact"]["fields"].items():
        if external_field in data:
            data[local_field] = data[external_field]
    if "salutation" in data and data["salutation"] == "47":
        data["salutation"] = "ms"
    else:
        data["salutation"] = "mr"
    if "street" not in data or data["street"] is None or data["street"] is False:
        data["street"] = ""
    if "street_nb" not in data or data["street_nb"] is None or data["street_nb"] is False:
        data["street_nb"] = ""
    if "zip" not in data or data["zip"] is None or data["zip"] is False:
        data["zip"] = ""
    if "city" not in data or data["city"] is None or data["city"] is False:
        data["city"] = ""
    return data


def get_contact(id):
    config = get_settings(section="external/bitrix24")
    data = post("crm.contact.get", {
        "ID": id
    })

    if "result" in data and len(data["result"]) > 0:
        return convert_config_values(data["result"])
    else:
        print("error:", data)
    return None


def get_contact_by_email(email):
    if email is None:
        return None
    data = post("crm.contact.list", {
        "filter[EMAIL]": email.strip()
    })
    if "result" in data:
        if len(data["result"]) == 0:
            return None
        return convert_config_values(data["result"][0])
    else:
        print("error:", data)
    return None


def add_contact(data, domain=None):
    config = get_settings(section="external/bitrix24")
    fields = config["contact"]["fields"]
    update_data = {}
    for key in data.keys():
        if key == "salutation":
            if data[key] == "ms":
                data[key] = "47"
            else:
                data[key] = "45"
    update_data = flatten_dict(data, update_data, fields=fields, config=config)
    response = post("crm.contact.add", update_data, domain=domain)
    if "result" in response and response["result"]:
        return get_contact(int(response["result"]))
    else:
        return False
