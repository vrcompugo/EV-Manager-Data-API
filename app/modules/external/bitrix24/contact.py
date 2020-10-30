from app.modules.settings import get_settings

from ._connector import get, post


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
    if data["salutation"] == "47":
        data["salutation"] = "ms"
    else:
        data["salutation"] = "mr"
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


def add_contact(data, domain=None):
    update_data = {}
    for key in data.keys():
        value = data[key]
        update_data[f"fields[{key.upper()}]"] = value
    response = post("crm.contact.add", update_data, domain=domain)
    print(response)
    if "result" in response and response["result"]:
        return int(response["result"])
    else:
        return False
