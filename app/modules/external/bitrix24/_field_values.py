import json


def convert_field_select_from_remote(field, data, config):

    if field in config["select_lists"] and field in data:
        if data[field] in config["select_lists"][field]:
            return config["select_lists"][field][data[field]]
    return None


def convert_field_euro_from_remote(field, data):
    if data[field] is None or data[field] == "":
        return None
    if type(data[field]) is int or type(data[field]) is float:
        return data[field]
    value = str(data[field])
    if value.find("|") < 0:
        return float(value)
    value = value[:value.find("|")]
    if len(value) > 3 and value[-3] == ",":
        value = value.replace(',', '.')
    if value == "":
        return 0
    return float(value)
