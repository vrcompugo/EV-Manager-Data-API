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
        if external_field.lower() in data:
            data[local_field] = data[external_field.lower()]
        if external_field in data:
            data[local_field] = data[external_field]
    if "salutation" in data and data["salutation"] == "HNR_DE_1":
        data["salutation"] = "ms"
    else:
        data["salutation"] = "mr"
    if "first_name" in data:
        data["firstname"] = data["first_name"]
    if "last_name" in data:
        data["lastname"] = data["last_name"]
    if "street" not in data or data["street"] is None or data["street"] is False:
        data["street"] = ""
    if "street_nb" not in data or data["street_nb"] is None or data["street_nb"] is False:
        data["street_nb"] = ""
    if "zip" not in data or data["zip"] is None or data["zip"] is False:
        data["zip"] = ""
    if "city" not in data or data["city"] is None or data["city"] is False:
        data["city"] = ""
    return data


def get_contact(id, force_reload=False):
    config = get_settings(section="external/bitrix24")
    data = post("crm.contact.get", {
        "ID": id
    }, force_reload=force_reload)

    if "result" in data and len(data["result"]) > 0:
        return convert_config_values(data["result"])
    else:
        print("error get contact:", data)
    return None


def get_contacts_by_changedate(changedate):
    payload = {
        "FILTER[>DATE_MODIFY]": str(changedate),
        "start": 0
    }
    result = []
    while payload["start"] is not None:
        data = post("crm.contact.list", payload)
        if "result" in data:
            payload["start"] = data["next"] if "next" in data else None
            for item in data["result"]:
                result.append(convert_config_values(item))
        else:
            print("error3:", data)
            payload["start"] = None
            return None
    return result


def get_contacts(payload, force_reload=False):
    payload["start"] = 0
    result = []
    if "SELECT" in payload and payload["SELECT"] == "full":
        del payload["SELECT"]
        config = get_settings(section="external/bitrix24")
        payload["SELECT[0]"] = "*"
        payload["SELECT[1]"] = "EMAIL"
        for index, field in enumerate(config["contact"]["fields"]):
            payload[f"SELECT[{index + 2}]"] = config["contact"]["fields"][field]
    while payload["start"] is not None:
        data = post("crm.contact.list", payload, force_reload=force_reload)
        if "result" in data:
            payload["start"] = data["next"] if "next" in data else None
            for item in data["result"]:
                result.append(convert_config_values(item))
        else:
            print("error3:", data)
            payload["start"] = None
            return None
    return result


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
        print("error get contact by email:", data)
    return None


def add_contact(data, domain=None):
    config = get_settings(section="external/bitrix24")
    fields = config["contact"]["fields"]
    update_data = {}
    for key in data.keys():
        if key == "salutation":
            if data[key] == "ms":
                data[key] = "HNR_DE_1"
            else:
                data[key] = "HNR_DE_2"
    update_data = flatten_dict(data, update_data, fields=fields, config=config)
    response = post("crm.contact.add", update_data, domain=domain)
    if "result" in response and response["result"]:
        return get_contact(int(response["result"]), force_reload=True)
    else:
        return False


def update_contact(id, data, domain=None):
    update_data = {"id": id}
    print("update_contact_run", id)
    config = get_settings(section="external/bitrix24", domain_raw=domain)
    fields = config["contact"]["fields"]
    update_data = flatten_dict(data, update_data, fields=fields, config=config)
    response = post("crm.contact.update", update_data, domain=domain)
    if "result" in response and response["result"]:
        return response["result"]
    else:
        return False
