from app import db
import pprint

from app.models import Customer
from app.modules.customer.services.customer_services import add_item, update_item

from ._connector import post, get
from ._association import find_association, associate_item


def filter_input(item_data):
    if "INTERESTEDNO" not in item_data:
        return None
    if "CUSTKIND" not in item_data:
        return None
    if "EMAIL" not in item_data:
        return None
    company_name = ""
    if item_data["CUSTKIND"] == 0:
        company_name = item_data["NAME1"]
        if item_data["NAME3"] is not None:
            company_name += " " + item_data["NAME3"]

    data = {
        "customer_number": str(item_data["CUSTNO"]) if item_data["CUSTNO"] is not None else None,
        "lead_number": str(item_data["INTERESTEDNO"]) if item_data["INTERESTEDNO"] is not None else None,
        "company": company_name,
        "salutation": item_data["CUSTNO"],
        "title": item_data["TITLE"],
        "firstname": item_data["NAME2"],
        "lastname": item_data["NAME1"] if item_data["CUSTKIND"] == 1 else "",
        "email": item_data["EMAIL"],
        "phone": item_data["PHONE1"],
        "birthday": item_data["BIRTHDAY"],
        "comment": item_data["NOTES"],
        "default_address": {
            "company": company_name,
            "salutation": item_data["CUSTNO"],
            "title": item_data["TITLE"],
            "firstname": item_data["NAME2"],
            "lastname": item_data["NAME1"] if item_data["CUSTKIND"] == 1 else "",
            "street": item_data["STREET"],
            "zip": item_data["ZIPCODE"],
            "city": item_data["CITY"]
        }
    }
    return data


def run_import():
    pass


def import_by_lead_number(lead_number):

    item = get("leads/{}".format(lead_number))
    if "data" in item and len(item["data"]) > 0:
        customer = None
        if "data" not in item or len(item["data"]) == 0:
            return None
        data = filter_input(item["data"][0])
        if data is None:
            print(item["data"][0])
            return None
        if data['email'] is not None:
            customer = Customer.query.filter_by(email=data['email']).first()
        if customer is None and data['customer_number'] is not None:
            customer = Customer.query.filter_by(customer_number=data['customer_number']).first()
        if customer is None and data['lead_number'] is not None:
            customer = Customer.query.filter_by(lead_number=data['lead_number']).first()
        if customer is None:
            return add_item(data)
        else:
            return update_item(customer.id, filter_input(data))
    return None
