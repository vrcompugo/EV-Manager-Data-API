from app import db
import pprint
from datetime import datetime, timedelta

from app.models import Reseller
from app.modules.lead.lead_services import add_item, update_item
from app.modules.settings.settings_services import get_one_item as get_config_item, update_item as update_config_item

from ._connector import post, get
from ._association import find_association, associate_item
from .customer import run_export as run_customer_export


def filter_import_data(item_data):
    data = {

    }
    return data


def filter_export_data(lead):
    return None


def run_import(minutes=None):
    print("Loading Reseller List")
    users = post("user.search", {
        "fields[USER_TYPE]": "employee"
    })
    if "result" in users:
        users = users["result"]
        for user in users:
            print(user["EMAIL"])
            reseller = Reseller.query.filter(Reseller.email == user["EMAIL"]).first()
            if reseller is not None:
                associate_item(model="Reseller", local_id=reseller.id, remote_id=user["ID"])


def run_export(remote_id=None, local_id=None):
    pass
