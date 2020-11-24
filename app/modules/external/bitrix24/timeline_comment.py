from app.modules.settings import get_settings

from ._connector import get, post
from ._field_values import flatten_dict


def add_timeline_comment(data, domain=None):
    config = get_settings(section="external/bitrix24")
    fields = config["timeline_comment"]["fields"]
    update_data = {}
    update_data = flatten_dict(data, update_data, fields=fields, config=config)
    response = post("crm.timeline.comment.add", update_data, domain=domain)
    if "result" in response and response["result"]:
        return int(response["result"])
    else:
        return False
