import json
from operator import index
from app.modules.settings import get_settings

from ._connector import get, post
from ._field_values import flatten_dict


def convert_config_values(data_raw):
    config = get_settings(section="external/bitrix24")
    data = {}
    for key in data_raw.keys():
        if key[:2].lower() == "uf":
            data[key] = data_raw[key]
        else:
            data[key] = data_raw[key]
            data[key.lower()] = data_raw[key]
    for local_field, external_field in config["task"]["fields"].items():
        if external_field.lower() in data:
            data[local_field] = data[external_field.lower()]
        if external_field in data:
            data[local_field] = data[external_field]
    return data


def get_task(id, with_comments=False):
    data = post("tasks.task.get", {
        "taskId": id,
        "select[0]": "TITLE",
        "select[1]": "DESCRIPTION",
        "select[2]": "UF_CRM_TASK",
        "select[3]": "CONTACT_ID",
        "select[4]": "COMPANY_ID",
        "select[5]": "TIME_ESTIMATE",
        "select[6]": "UF_AUTO_422491195439",
        "select[7]": "STATUS",
        "select[8]": "START_DATE_PLAN",
        "select[9]": "END_DATE_PLAN",
        "select[10]": "RESPONSIBLE_ID",
        "select[11]": "ACCOMPLICES",
        "select[12]": "SUBORDINATE",
        "select[13]": "AUDITORS",
        "select[14]": "DEADLINE",
        "select[15]": "UF_AUTO_219922666303",
        "select[16]": "UF_AUTO_343721853755",
        "select[17]": "UF_AUTO_513701476131"
    })
    if "result" in data:
        task_data = convert_config_values(data["result"]["task"])
        comments = post("task.commentitem.getlist", {
            "taskId": id
        })
        if "result" in comments:
            task_data["comments"] = comments["result"]
        return task_data
    else:
        print("error get lead:", data)
    return None


def get_tasks(payload):
    payload["start"] = 0
    if "select" in payload and payload["select"] == "full":
        del payload["select"]
        config = get_settings(section="external/bitrix24")
        payload["select[0]"] = "*"
        for index, field in enumerate(config["task"]["fields"]):
            payload[f"select[{index + 1}]"] = "UF_AUTO_" + config["task"]["fields"][field].replace("ufAuto", "")
    result = []
    while payload["start"] is not None:
        data = post("tasks.task.list", payload)
        if "result" in data:
            payload["start"] = data["next"] if "next" in data else None
            for item in data["result"]["tasks"]:
                result.append(convert_config_values(item))
        else:
            print("error3:", data)
            payload["start"] = None
            return None
    return result


def update_task(id, data, domain=None):
    update_data = {"taskId": id}
    config = get_settings(section="external/bitrix24", domain_raw=domain)
    fields = config["task"]["fields"]
    update_data = flatten_dict(data, update_data, fields=fields, config=config)
    if "fields[ufAuto422491195439]" in update_data:
        update_data["fields[UF_AUTO_422491195439]"] = update_data["fields[ufAuto422491195439]"]
    if "fields[ufAuto219922666303]" in update_data:
        update_data["fields[UF_AUTO_219922666303]"] = update_data["fields[ufAuto219922666303]"]
    if "fields[ufAuto343721853755]" in update_data:
        update_data["fields[UF_AUTO_343721853755]"] = update_data["fields[ufAuto343721853755]"]
    if "fields[ufAuto513701476131]" in update_data:
        update_data["fields[UF_AUTO_513701476131]"] = update_data["fields[ufAuto513701476131]"]
    response = post("tasks.task.update", update_data, domain=domain)
    if "result" in response and response["result"]:
        return response["result"]
    else:
        print(json.dumps(response, indent=2))
        print(json.dumps(update_data, indent=2))
        return False
