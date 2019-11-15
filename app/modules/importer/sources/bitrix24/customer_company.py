from datetime import datetime, timedelta

from app.models import Customer
from app.modules.lead.lead_services import add_item, update_item
from app.modules.settings.settings_services import get_one_item as get_config_item, update_item as update_config_item

from ._connector import post, get
from ._association import find_association, associate_item


def filter_export_data(customer):
    if customer.company is None or customer.company == "":
        return None
    data = {
        "fields[TITLE]": customer.company,
        "fields[COMPANY_TYPE]": "Kunde",
        "fields[CURRENCY_ID]": "EUR"
    }
    return data


def run_export(remote_id=None, local_id=None):
    customer = None
    if local_id is not None:
        customer = Customer.query.get(local_id)
    if remote_id is not None:
        lead_association = find_association("CustomerCompany", remote_id=remote_id)
        customer = Customer.query.get(lead_association.local_id)
    if customer is not None:
        post_data = filter_export_data(customer)
        if post_data is not None:
            remote_association = find_association("CustomerCompany", local_id=customer.id)
            if remote_association is None:
                response = post("crm.company.add", post_data=post_data)
                if "result" in response:
                    associate_item(model="CustomerCompany", local_id=customer.id, remote_id=response["result"])
            else:
                post_data["id"] = remote_association.remote_id
                response = post("crm.company.update", post_data=post_data)
            print(response)
