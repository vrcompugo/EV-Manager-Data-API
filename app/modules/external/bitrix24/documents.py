import json

from app.modules.settings import get_settings

from ._connector import post, get, list_request_invoice


def convert_config_values(data_raw):
    return data_raw

def get_documents(payload):
    payload["start"] = 0
    result = []
    list_request_invoice("crm.documentgenerator.document.list", payload, result, convert_config_values)
    return result
