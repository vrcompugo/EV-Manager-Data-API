import pprint
from app.models import Customer

from ._connector import post, get
from ._association import find_association, associate_item
from .customer_company import run_export as run_company_export


def filter_import_data(item_data):
    data = {

    }
    return data


def filter_export_data(customer: Customer):


    data = {
        "fields[HONORIFIC]": "HNR_DE_1" if customer.salutation == "ms" else "HNR_DE_2",
        "fields[NAME]": customer.firstname,
        "fields[LAST_NAME]": customer.lastname,
        "fields[UF_CRM_1572950758]": customer.default_address.street,
        "fields[UF_CRM_1572950777]": customer.default_address.street_nb,
        "fields[UF_CRM_1572963448]": customer.default_address.city,
        "fields[UF_CRM_1572963458]": customer.default_address.zip,
        "fields[EMAIL][0][TYPE_ID]": "EMAIL",
        "fields[EMAIL][0][VALUE]": customer.email,
        "fields[EMAIL][0][VALUE_TYPE]": "WORK",
        "fields[TYPE_ID]": "CLIENT",
    }
    if customer.company is not None and customer.company != "":
        run_company_export(local_id=customer.id)
        company_link = find_association(model="CustomerCompany", local_id=customer.id)
        if company_link is None:
            return None
        data["fields[COMPANY_ID]"] = company_link.remote_id
    return data


def run_import(remote_id=None, local_id=None):
    response = post("crm.contact.get", post_data={
        "ID": remote_id
    })
    pp = pprint.PrettyPrinter()
    pp.pprint(response)
    return True


def run_export(remote_id=None, local_id=None):
    customer = None
    if local_id is not None:
        customer = Customer.query.get(local_id)
    if remote_id is not None:
        remote_association = find_association("Customer", remote_id=remote_id)
        customer = Customer.query.get(remote_association.local_id)
    if customer is not None:
        post_data = filter_export_data(customer)
        print("export customer: ", post_data)
        if post_data is not None:
            remote_association = find_association("Customer", local_id=customer.id)
            if remote_association is None:
                response = post("crm.contact.add", post_data=post_data)
                if "result" in response:
                    associate_item(model="Customer", local_id=customer.id, remote_id=response["result"])
                    if "fields[COMPANY_ID]" in post_data:
                        post_data["id"] = remote_association.remote_id
                        post("crm.contact.company.add", post_data=post_data)
            else:
                post_data["id"] = remote_association.remote_id
                response = post("crm.contact.update", post_data=post_data)
                if "fields[COMPANY_ID]" in post_data:
                    print(
                        post("crm.contact.company.add", post_data={
                            "id": remote_association.remote_id,
                            "fields[COMPANY_ID]": post_data["fields[COMPANY_ID]"],
                            "fields[IS_PRIMARY ]": 0,
                            "fields[SORT]": 0,
                        }))
