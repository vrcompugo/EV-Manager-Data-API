import json
import pprint
import datetime

from app.models import Survey
from app.utils.error_handler import error_handler
from app.modules.settings.settings_services import get_one_item as get_config_item, update_item as update_config_item

from ._connector import post, get
from ._association import find_association, associate_item
from .order import run_import as order_import


def filter_export_data(item_data):
    return None


def run_export(local_id=None):
    survey = Survey.query.filter(Survey.id == local_id).first()
    if survey is None:
        return None
    lead_link = find_association("Lead", local_id=survey.lead_id)
    if lead_link is None:
        return None
    response = post("crm.lead.get", {
        "ID": lead_link.remote_id
    })
    response = post("crm.lead.update", {
        "ID": lead_link.remote_id,
        "fields[UF_CRM_1572968349][0]": "https://keso.bitrix24.de/rest/106/v38b9iovomrydti2/download/?token=disk%7CaWQ9MzI2OTIyJl89UEtLUEJockNqbmgzRVpkcTJlVGM2QnNaaUVpOXlXc1E%3D%7CImRvd25sb2FkfGRpc2t8YVdROU16STJPVEl5Smw4OVVFdExVRUpvY2tOcWJtZ3pSVnBrY1RKbFZHTTJRbk5hYVVWcE9YbFhjMUU9fDEwNnx5eWQxMHJhdTZvZDNqbGFuIg%3D%3D.RqkXLEtpiFKYRdfSrQrT7tHyXo0frMlDd3tP4l8Yhko%3D"
    })
    print(json.dumps(response, indent=2))
    response = post("crm.lead.get", {
        "ID": lead_link.remote_id
    })
    print(json.dumps(response, indent=2))
    response = post("disk.folder.getchildren", {
        "id": 326908
    })
    response = post("crm.lead.userfield.list", {
        "filter[=FIELD_NAME]": "UF_CRM_1572968349"
    })
    print(json.dumps(response, indent=2))
    return None
