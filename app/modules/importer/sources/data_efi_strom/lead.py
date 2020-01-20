import pprint

from app import db
from app.models import Lead, Customer

from ._connector import post, get, put
from ._association import find_association, associate_item


def filter_import_input(data):
    pass


def filter_export_input(lead):
    customer_address = lead.customer.default_address.__dict__
    if "_sa_instance_state" in customer_address:
        del customer_address["_sa_instance_state"]
    if "customer_id" in customer_address:
        del customer_address["customer_id"]
    data = {
        "kez_id": None,
        "customer_number": None,
        "lead_number": lead.number,
        "salutation": lead.customer.salutation,
        "title": lead.customer.title,
        "firstname": lead.customer.firstname,
        "lastname": lead.customer.lastname,
        "company": lead.customer.company,
        "phonenumber_prefix": "",
        "phonenumber": lead.customer.phone,
        "email": lead.customer.email,
        "default_address": customer_address,
        "master_customer": False
    }
    return data


def run_import(local_id=None, remote_id=None):
    pass


def run_export(local_id=None, remote_id=None):
    pp = pprint.PrettyPrinter()
    lead = None
    if str(local_id).find("lead_number:") == 0:
        lead_number = str(local_id).replace("lead_number:", "")
        lead = Lead.query.filter(Lead.number == lead_number).first()
        if lead is not None:
            local_id = lead.id
        else:
            local_id = None
    if local_id is not None:
        lead = Lead.query.get(local_id)
    if remote_id is not None:
        remote_association = find_association("Lead", remote_id=remote_id)
        lead = Lead.query.get(remote_association.local_id)
    if lead is not None:
        data = filter_export_input(lead)
        if data is not None:
            remote_association = find_association("Lead", local_id=local_id)
            if remote_association is None:
                response = put("Customer/-1", post_data={"item": data})
                if "item" in response and "id" in response["item"]:
                    associate_item(model="Lead", local_id=lead.id, remote_id=response["item"]["id"])
            else:
                response = put("Customer/{}".format(remote_association.remote_id), post_data={"item": data})
            print(response)
