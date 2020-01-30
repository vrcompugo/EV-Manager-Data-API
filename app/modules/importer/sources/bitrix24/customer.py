import pprint

from app.models import Customer
from app.modules.customer.services.customer_services import add_item, update_item

from ._connector import post, get
from ._association import find_association, associate_item
from .customer_company import run_export as run_company_export


def filter_import_data(item_data):

    reseller_accociation = find_association("Reseller", remote_id=item_data["ASSIGNED_BY_ID"])
    if reseller_accociation is None:
        reseller_id = None
    else:
        reseller_id = reseller_accociation.local_id

    company = ""
    if item_data["COMPANY_ID"] is not None and int(item_data["COMPANY_ID"]) > 0:
        response = post("crm.company.get", post_data={
            "ID": item_data["COMPANY_ID"]
        })
        if "result" in response and "TITLE" in response["result"]:
            company = response["result"]["TITLE"]

    data = {
        "UPDATE_IF_EXISTS": True,
        "reseller_id": reseller_id,
        "customer_number": None,
        "lead_number": None,
        "company": company,
        "salutation": "ms" if item_data["HONORIFIC"] == "HNR_DE_1" else "mr",
        "title": "",
        "firstname": item_data["NAME"],
        "lastname": item_data["LAST_NAME"],
        "pending_email": None,
        "email_status": None,
        "last_change": item_data["DATE_MODIFY"],
        "default_address": {
            "company": company,
            "salutation": "ms" if item_data["HONORIFIC"] == "HNR_DE_1" else "mr",
            "title": "",
            "firstname": item_data["NAME"],
            "lastname": item_data["LAST_NAME"],
            "street": item_data["UF_CRM_1572950758"],
            "street_nb": item_data["UF_CRM_1572950777"],
            "street_extra": "",
            "zip": item_data["UF_CRM_1572963458"],
            "city": item_data["UF_CRM_1572963448"],
            "status": "ok"
        }
    }
    if "EMAIL" in item_data and len(item_data["EMAIL"]) > 0:
        data["email"] = item_data["EMAIL"][0]["VALUE"]
    if "PHONE" in item_data and len(item_data["PHONE"]) > 0:
        data["phone"] = item_data["PHONE"][0]["VALUE"]
    return data


def filter_export_data(customer: Customer):

    reseller_link = find_association("Reseller", local_id=customer.reseller_id)
    if customer.firstname is None or customer.firstname == "":
        customer_name = customer.company
    else:
        customer_name = customer.firstname
    data = {
        "fields[HONORIFIC]": "HNR_DE_1" if customer.salutation == "ms" else "HNR_DE_2",
        "fields[NAME]": customer_name,
        "fields[LAST_NAME]": customer.lastname,
        "fields[TYPE_ID]": "CLIENT",
        "email": customer.email,
        "phone": customer.phone
    }

    if customer.default_address is not None:
        data["fields[UF_CRM_1572950758]"] = customer.default_address.street
        data["fields[UF_CRM_1572950777]"] = customer.default_address.street_nb
        data["fields[UF_CRM_1572963448]"] = customer.default_address.city
        data["fields[UF_CRM_1572963458]"] = customer.default_address.zip

    if reseller_link is not None:
        data["fields[ASSIGNED_BY_ID]"] = reseller_link.remote_id

    if customer.email is not None:
        data["fields[EMAIL][0][TYPE_ID]"] = "EMAIL"
        data["fields[EMAIL][0][VALUE]"] = customer.email
        data["fields[EMAIL][0][VALUE_TYPE]"] = "WORK"

    if customer.phone is not None and customer.phone != "" and customer.phone != "None":
        data["fields[PHONE][0][TYPE_ID]"] = "PHONE"
        data["fields[PHONE][0][VALUE]"] = customer.phone
        data["fields[PHONE][0][VALUE_TYPE]"] = "WORK"

    if customer.company is not None and customer.company != "":
        run_company_export(local_id=customer.id)
        company_link = find_association(model="CustomerCompany", local_id=customer.id)
        if company_link is None:
            return None
        data["fields[COMPANY_ID]"] = company_link.remote_id
    return data


def run_import(remote_id=None, local_id=None):
    if local_id is not None:
        customer_link = find_association("Customer", local_id=local_id)
        remote_id = customer_link.remote_id
    if remote_id is not None:
        response = post("crm.contact.get", post_data={
            "ID": remote_id
        })
        if "result" in response:
            data = filter_import_data(response["result"])
            if data is not None:
                print("importing customer")
                customer_link = find_association("Customer", remote_id=remote_id)
                if customer_link is None:
                    customer = add_item(data)
                    associate_item(model="Customer", local_id=customer.id, remote_id=remote_id)
                else:
                    del data["number"]
                    customer = update_item(customer_link.local_id, data)
                return customer
            else:
                print("data is not customer import: ", response["result"])
    return None


def run_customer_lead_import(lead_item_data):
    remote_id = lead_item_data["ID"]
    lead_item_data["UF_CRM_1572950758"] = lead_item_data["UF_CRM_5DD4020221169"]
    lead_item_data["UF_CRM_1572950777"] = lead_item_data["UF_CRM_5DD402022E300"]
    lead_item_data["UF_CRM_1572963458"] = lead_item_data["UF_CRM_5DD4020242167"]
    lead_item_data["UF_CRM_1572963448"] = lead_item_data["UF_CRM_5DD4020239456"]
    data = filter_import_data(lead_item_data)
    if data is not None:
        print("importing customer")
        customer_link = find_association("LeadCustomer", remote_id=remote_id)
        if customer_link is None:
            customer = add_item(data)
            associate_item(model="LeadCustomer", local_id=customer.id, remote_id=remote_id)
        else:
            del data["number"]
            customer = update_item(customer_link.local_id, data)
        return customer
    else:
        print("data is not customer import: ", response["result"])
    return None


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
                    remote_association = associate_item(model="Customer", local_id=customer.id, remote_id=response["result"])
            else:
                post_data["id"] = remote_association.remote_id
                response = post("crm.contact.get", post_data=post_data)
                if "result" in response and "EMAIL" in response["result"]:
                    for email in response["result"]["EMAIL"]:
                        if post_data["email"] is not None and email["VALUE"] == post_data["email"]:
                            if "fields[EMAIL][0][TYPE_ID]" in post_data:
                                del post_data["fields[EMAIL][0][TYPE_ID]"]
                            if "fields[EMAIL][0][VALUE]" in post_data:
                                del post_data["fields[EMAIL][0][VALUE]"]
                            if "fields[EMAIL][0][VALUE_TYPE]" in post_data:
                                del post_data["fields[EMAIL][0][VALUE_TYPE]"]
                if "result" in response and "PHONE" in response["result"]:
                    for phone in response["result"]["PHONE"]:
                        if post_data["phone"] is not None and phone["VALUE"] == post_data["phone"]:
                            if "fields[PHONE][0][TYPE_ID]" in post_data:
                                del post_data["fields[PHONE][0][TYPE_ID]"]
                            if "fields[PHONE][0][VALUE]" in post_data:
                                del post_data["fields[PHONE][0][VALUE]"]
                            if "fields[PHONE][0][VALUE_TYPE]" in post_data:
                                del post_data["fields[PHONE][0][VALUE_TYPE]"]
                response = post("crm.contact.update", post_data=post_data)
