import json
import requests

from app.modules.settings import get_settings
from app.modules.external.bitrix24.contact import get_contact
from app.modules.external.bitrix24.documents import get_documents as get_documents_bitrix

from ._connector import get, post, list_request
from ._field_values import flatten_dict


def convert_config_values(data_raw):
    config = get_settings(section="external/bitrix24")
    data = {}
    for key in data_raw.keys():
        if key[:2] == "UF":
            data[key] = data_raw[key]
        else:
            data[key.lower()] = data_raw[key]

    for local_field, external_field in config["invoice"]["fields"].items():
        if external_field.lower() in data:
            data[local_field] = data[external_field.lower()]
        if external_field in data:
            data[local_field] = data[external_field]
        if local_field in data and local_field in config["select_lists"]:
            if isinstance(data[local_field], list):
                for index in range(len(data[local_field])):
                    if str(data[local_field][index]) in config["select_lists"][local_field]:
                        data[local_field][index] = config["select_lists"][local_field][str(data[local_field][index])]
            else:
                if str(data[local_field]) in config["select_lists"][local_field]:
                    data[local_field] = config["select_lists"][local_field][str(data[local_field])]
    prefix = data.get("invoice_document_prefix")
    if data.get("invoice_document_prefix") is None:
        prefix = "RG-"
    data["number"] = f"{prefix}{data.get('invoice_number_index')}"
    data["opportunity"] = float(data["opportunity"])
    print(json.dumps(data, indent=2))
    data["tax_value"] = float(data["taxvalue"])
    data["contact"] = {}
    data["customer_number"] = None
    if data.get("user_number") not in [None, ""]:
        data["customer_number"] = f'U-{data.get("user_number")}'
    if data.get("zip_city") not in [None, ""]:
        parts = data.get("zip_city").split(" ")
        data["zip"] = parts[0]
        data["city"] = " ".join(parts[1:])
    if "contact_id" in data and data["contact_id"] is not None and data["contact_id"] is not False and data["contact_id"] != "" and int(data["contact_id"]) > 0:
        contact_data = get_contact(data["contact_id"], force_reload=True)
        if contact_data is not None:
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
                "city": contact_data["city"],
                "customer_number": contact_data["fakturia_number"]
            }
            if data.get("first_name") in [None, ""]:
                data["first_name"] = contact_data["first_name"]
            if data.get("last_name") in [None, ""]:
                data["last_name"] = contact_data["last_name"]
            if data.get("street") in [None, ""]:
                data["street"] = f'{contact_data["street"]} {contact_data["street_nb"]}'
            if data.get("zip_city") in [None, ""]:
                data["zip"] = contact_data["zip"]
                data["city"] = contact_data["city"]
            if data.get("customer_number") in [None, ""]:
                data["customer_number"] = contact_data["fakturia_number"]
            if data.get("email") in [None, ""]:
                data["email"] = contact_data["email"]

    return data


def get_invoice(id):
    config = get_settings(section="external/bitrix24")
    data = post("crm.item.get", {
        "entityTypeId": 31,
        "ID": id
    })

    if "result" in data and len(data["result"]) > 0:
        return convert_config_values(data["result"])
    else:
        print("error get company:", data)
    return None


def get_invoices(payload, force_reload=False):
    payload["start"] = 0
    payload["entityTypeId"] = 31
    result = []
    if "SELECT" in payload and payload["SELECT"] == "full":
        del payload["SELECT"]
        config = get_settings(section="external/bitrix24")
        payload["SELECT[0]"] = "*"
        for index, field in enumerate(config["invoice"]["fields"]):
            payload[f"SELECT[{index + 1}]"] = config["invoice"]["fields"][field]
    list_request("crm.item.list", payload, result, convert_config_values, force_reload=force_reload)
    return result


def get_document(invoice_id):
    documents = get_documents_bitrix({
        "filter[entityId]": invoice_id,
        "filter[entityTypeId]": 31,
        "order[updateTime]": "desc"
    })
    if documents is not None and len(documents) > 0:
        print(json.dumps(documents, indent=2))
        response = requests.get(documents[0]["pdfUrlMachine"])
        return response.content

    return None