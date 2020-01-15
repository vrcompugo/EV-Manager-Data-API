import pprint
from datetime import datetime, timedelta

from app import db
from app.models import Reseller
from app.modules.lead.lead_services import add_item, update_item
from app.modules.reseller.services.reseller_services import update_item as update_reseller
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
    from app.utils.google_geocoding import geocode_address

    print("Loading Reseller List")
    users_data = {
        "next": 0
    }
    while "next" in users_data:
        users_data = post("user.search", {
            "fields[USER_TYPE]": "employee",
            "start": users_data["next"]
        })
        if "result" in users_data:
            users = users_data["result"]
            for user in users:
                reseller = Reseller.query.filter(Reseller.email == user["EMAIL"]).first()
                if reseller is not None:
                    print(user["EMAIL"])
                    if reseller.sales_center is not None and reseller.sales_lat is None:
                        location = geocode_address(reseller.sales_center)
                        if location is not None:
                            print(location)
                            update_reseller(reseller.id, {
                                "sales_lat": location["lat"],
                                "sales_lng": location["lng"]
                            })
                    associate_item(model="Reseller", local_id=reseller.id, remote_id=user["ID"])


def run_export(remote_id=None, local_id=None):
    pass
