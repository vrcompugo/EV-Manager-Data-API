from app import db
import pprint
from datetime import datetime, timedelta

from app.models import Lead
from app.modules.lead.lead_services import add_item, update_item
from app.modules.settings.settings_services import get_one_item as get_config_item, update_item as update_config_item

from ._connector import post, get
from ._association import find_association, associate_item
from .customer import run_export as run_customer_export


def filter_import_input(item_data):
    data = {

    }
    return data


def filter_export_input(lead):

    if not lead.reseller_id > 0:
        return None

    '''reseller_link = find_association("Reseller", local_id=lead.reseller_id)
    if reseller_link is None:
        return None'''
    customer_link = find_association("Customer", local_id=lead.customer_id)
    if customer_link is None:
        run_customer_export(local_id=lead.customer_id)
        customer_link = find_association("Customer", local_id=lead.customer_id)
        if customer_link is None:
            return None
    status = "NEW"
    if lead.status == "contacted":
        status = "IN_PROCESS"
    if lead.status == "survey_created":
        status = "1"
    if lead.status == "offer_created":
        status = "2"
    if lead.status == "offer_presented":
        status = "3"
    if lead.status == "offer_negotiation":
        status = "5"
    if lead.status == "lost":
        status = "6"
    if lead.status == "won":
        status = "PROCESSED"

    data = {
        "fields[TITLE]": (lead.customer.company + " " + lead.customer.lastname).strip(),
        "fields[NAME]": lead.customer.firstname,
        "fields[LAST_NAME]": lead.customer.lastname,
        "fields[STATUS_ID]": status,
        "fields[CONTACT_ID]": customer_link.remote_id,
        "fields[COMPANY_TITLE]": lead.customer.company,
        "fields[OPENED]": "Y"
        #"fields[ASSIGNED_BY_ID]": reseller_link.remote_id
    }

    company_link = find_association("CustomerCompany", local_id=lead.customer_id)
    if company_link is not None:
        data["fields[COMPANY_ID]"] = company_link.remote_id
    return data


def run_import(minutes=None):
    pass


def run_export(remote_id=None, local_id=None):
    lead = None
    if local_id is not None:
        lead = Lead.query.get(local_id)
    if remote_id is not None:
        lead_association = find_association("Lead", remote_id=remote_id)
        lead = Lead.query.get(lead_association.local_id)
    if lead is not None:
        post_data = filter_export_input(lead)
        if post_data is not None:
            lead_association = find_association("Lead", local_id=lead.id)
            if lead_association is None:
                response = post("crm.lead.add", post_data=post_data)
                if "result" in response:
                    associate_item(model="Lead", local_id=lead.id, remote_id=response["result"])

            else:
                post_data["id"] = lead_association.remote_id
                response = post("crm.lead.update", post_data=post_data)
                response = post("crm.lead.get", post_data=post_data)
            pp = pprint.PrettyPrinter(indent=2)
            pp.pprint(response)
