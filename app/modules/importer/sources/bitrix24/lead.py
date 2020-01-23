from app import db
import pprint
import time
import random
from datetime import datetime, timedelta
from sqlalchemy import and_
import traceback

from app.models import Lead, Customer
from app.modules.lead.lead_services import add_item, update_item
from app.modules.settings.settings_services import get_one_item as get_config_item, update_item as update_config_item

from ._connector import post, get
from ._association import find_association, associate_item
from .customer import run_export as run_customer_export, run_import as run_customer_import, run_customer_lead_import


LEAD_STATUS_CONVERT = {
    "new": "NEW",
    "contacted": "IN_PROCESS",
    "tel_not_connected": "5",
    "returned": "8",
    "survey_created": "4",
    "offer_created": "PROCESSED",
    "offer_presented": "1",
    "offer_negotiation": "1",
    "lost": "JUNK",
    "won": "CONVERTED",
}


def filter_import_input(item_data):
    customer_id = None
    customer = None
    if item_data["CONTACT_ID"] is not None and int(item_data["CONTACT_ID"]) > 0:
        customer_accociation = find_association("Customer", remote_id=item_data["CONTACT_ID"])
        if customer_accociation is None:
            customer = run_customer_import(remote_id=item_data["CONTACT_ID"])
            if customer is not None:
                customer_id = customer.id
        else:
            customer_id = customer_accociation.local_id
            customer = Customer.query.get(customer_accociation.local_id)
    else:
        customer_accociation = find_association("LeadCustomer", remote_id=item_data["ID"])
        if customer_accociation is None:
            customer = run_customer_lead_import(item_data)
            customer_id = customer.id
        else:
            customer_id = customer_accociation.local_id
            customer = Customer.query.get(customer_accociation.local_id)
    if customer.default_address.street == "false":
        customer.default_address.street = item_data["UF_CRM_5DD4020221169"]
        customer.default_address.street_nb = item_data["UF_CRM_5DD402022E300"]
        customer.default_address.zip = item_data["UF_CRM_5DD4020242167"]
        customer.default_address.city = item_data["UF_CRM_5DD4020239456"]
        db.session.commit()

    reseller_accociation = find_association("Reseller", remote_id=item_data["ASSIGNED_BY_ID"])
    if reseller_accociation is None:
        reseller_id = None
    else:
        reseller_id = reseller_accociation.local_id

    inv_map = {v: k for k, v in LEAD_STATUS_CONVERT.items()}
    status = None
    print(item_data["STATUS_ID"])
    if item_data["STATUS_ID"] in inv_map:
        status = inv_map[item_data["STATUS_ID"]]

    data = {
        "datetime": item_data["DATE_CREATE"],
        "last_update": item_data["DATE_MODIFY"],
        "reseller_id": reseller_id,
        "customer_id": customer_id,
        "value": item_data["OPPORTUNITY"],
        "status": status,
        "data": {
            "Vorname": item_data["NAME"],
            "Nachname/Firma": item_data["LAST_NAME"],
            "Stra\u00dfe": item_data["UF_CRM_5DD4020221169"] + " " + item_data["UF_CRM_5DD402022E300"],
            "PLZ": "" if item_data["UF_CRM_5DD4020242167"] is None else item_data["UF_CRM_5DD4020242167"],
            "Ort": "" if item_data["UF_CRM_5DD4020239456"] is None else item_data["UF_CRM_5DD4020239456"],
            "Quelle": "bitrix24",
            "Land": None,
            "Mobil": "",
            "Notiz": ""
        },
        "description": "Vorname: {}\n".format(item_data["NAME"])
                       + "Nachname/Firma: {}\n".format(item_data["LAST_NAME"])
                       + "Stra\u00dfe: {}\n".format(item_data["UF_CRM_5DD4020221169"] + " " + item_data["UF_CRM_5DD402022E300"])
                       + "PLZ: {}\n".format(item_data["UF_CRM_5DD4020242167"])
                       + "Ort: {}\n".format(item_data["UF_CRM_5DD4020239456"])
                       + "Quelle: {}\n".format("bitrix24")
                       + "Angelegt am: {}\n".format(item_data["DATE_CREATE"])
    }
    data["description_html"] = data["description"].replace("\n", "<br>\n")
    if customer is not None and customer.default_address is not None:
        data["address_id"] = customer.default_address.id
    return data


def get_remote_lead_status(lead):
    status = None
    if lead.status in LEAD_STATUS_CONVERT:
        status = LEAD_STATUS_CONVERT[lead.status]
    return status


def filter_export_input(lead):

    if lead.reseller_id is None or lead.reseller_id == 0:
        return None

    reseller_link = find_association("Reseller", local_id=lead.reseller_id)
    customer_link = find_association("Customer", local_id=lead.customer_id)
    status = get_remote_lead_status(lead)
    salutation = "0"
    if lead.customer.salutation is not None:
        if lead.customer.salutation == "mr":
            salutation = "HNR_DE_2"
        if lead.customer.salutation == "ms":
            salutation = "HNR_DE_1"

    street = lead.customer.default_address.street
    street_nb = lead.customer.default_address.street_nb
    if street_nb is None:
        last_space = street.rfind(" ")
        if last_space > 0:
            street_nb = street[last_space + 1:]
            street = street[0:last_space]
    data = {
        "fields[TITLE]": (("" if lead.customer.company is None else lead.customer.company + " ") + lead.customer.lastname).strip(),
        "fields[COMPANY_TITLE]": lead.customer.company,
        "fields[HONORIFIC]": salutation,
        "fields[NAME]": lead.customer.firstname,
        "fields[LAST_NAME]": lead.customer.lastname,
        "fields[HAS_EMAIL]": "N",
        "fields[UF_CRM_5DD4020221169]": street,
        "fields[UF_CRM_5DD402022E300]": street_nb,
        "fields[UF_CRM_5DD4020242167]": lead.customer.default_address.zip,
        "fields[UF_CRM_5DD4020239456]": lead.customer.default_address.city,
        "fields[UF_CRM_1578581226149]": lead.number,
        "fields[OPPORTUNITY]": lead.value,
        "fields[OPENED]": "Y",
        "email": lead.customer.email,
        "phone": lead.customer.phone
        # "fields[ASSIGNED_BY_ID]": reseller_link.remote_id
    }
    if status is not None:
        data["fields[STATUS_ID]"] = status
    if lead.customer.email and lead.customer.email != "folgt":
        data["fields[EMAIL][0][TYPE_ID]"] = "EMAIL"
        data["fields[EMAIL][0][VALUE]"] = lead.customer.email
        data["fields[EMAIL][0][VALUE_TYPE]"] = "WORK"
        data["fields[HAS_EMAIL]"] = "Y"
    if "Quelle" in lead.data:
        source_id = "OTHER"
        if lead.data["Quelle"] == "DAA":
            source_id = "1"
        if lead.data["Quelle"] == "WattFox":
            source_id = "2"
        if lead.data["Quelle"] == "Senec":
            source_id = "3"
        data["fields[SOURCE_ID]"] = source_id
        if source_id == "OTHER":
            data["fields[SOURCE_DESCRIPTION]"] = lead.data["Quelle"]

    if lead.customer.phone is not None and lead.customer.phone != "" and lead.customer.phone != "None":
        data["fields[PHONE][0][TYPE_ID]"] = "PHONE"
        data["fields[PHONE][0][VALUE]"] = lead.customer.phone
        data["fields[PHONE][0][VALUE_TYPE]"] = "WORK"

    if reseller_link is not None:
        data["fields[ASSIGNED_BY_ID]"] = reseller_link.remote_id
    if customer_link is not None:
        data["fields[CONTACT_ID]"] = customer_link.remote_id
    company_link = find_association("CustomerCompany", local_id=lead.customer_id)
    if company_link is not None:
        data["fields[COMPANY_ID]"] = company_link.remote_id
    return data


def run_import(remote_id=None, local_id=None):
    from app.modules.importer.sources.data_efi_strom.lead import run_export as run_data_efi_export
    pp = pprint.PrettyPrinter()
    if local_id is not None:
        lead_association = find_association("Lead", local_id=local_id)
        remote_id = lead_association.remote_id
    if remote_id is not None:
        response = post("crm.lead.get", post_data={"id": remote_id})
        if "result" in response:
            data = filter_import_input(response["result"])
            if data is not None:
                print("importing lead")
                lead_link = find_association("Lead", remote_id=remote_id)
                if lead_link is None:
                    lead = add_item(data)
                    associate_item(model="Lead", local_id=lead.id, remote_id=remote_id)
                    post_data = {
                        "id": remote_id,
                        "fields[UF_CRM_1578581226149]": lead.number
                    }
                    post("crm.lead.update", post_data=post_data)
                else:
                    lead = update_item(lead_link.local_id, data)
                if lead is not None:
                    run_data_efi_export(local_id=lead.id)


def run_export(remote_id=None, local_id=None):
    lead = None
    pp = pprint.PrettyPrinter()

    if local_id is not None:
        lead = Lead.query.get(local_id)
    if remote_id is not None:
        lead_association = find_association("Lead", remote_id=remote_id)
        lead = Lead.query.get(lead_association.local_id)
    if lead is not None:
        print("Lead Export", lead.id)
        post_data = filter_export_input(lead)
        if post_data is not None:
            lead_association = find_association("Lead", local_id=lead.id)
            if lead_association is None:
                response = post("crm.lead.add", post_data=post_data)
                if "result" in response:
                    associate_item(model="Lead", local_id=lead.id, remote_id=response["result"])
                else:
                    pp.pprint(response)
            else:
                post_data["id"] = lead_association.remote_id
                response = post("crm.lead.get", post_data=post_data)
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
                response = post("crm.lead.update", post_data=post_data)
                if "result" not in response:
                    pp.pprint(response)


def run_status_update_export(remote_id=None, local_id=None):
    if remote_id is not None:
        lead_association = find_association("Lead", remote_id=remote_id)
    if local_id is not None:
        lead_association = find_association("Lead", local_id=local_id)
    if lead_association is None:
        print("lead link not found", local_id, remote_id)
        return
    lead = Lead.query.get(lead_association.local_id)
    status = get_remote_lead_status(lead)
    post_data = {}
    post_data["id"] = lead_association.remote_id
    post_data["fields[STATUS_ID]"] = status
    post_data["fields[OPPORTUNITY]"] = float(lead.value)
    customer_link = find_association("Customer", local_id=lead.customer_id)
    if customer_link is not None:
        post_data["fields[CONTACT_ID]"] = customer_link.remote_id
    company_link = find_association("CustomerCompany", local_id=lead.customer_id)
    if company_link is not None:
        post_data["fields[COMPANY_ID]"] = company_link.remote_id
    response = post("crm.lead.update", post_data=post_data)
    if "result" not in response:
        pp.pprint(response)


def run_cron_export():
    from ..data_efi_strom.lead import run_export as run_data_efi_export
    config = get_config_item("importer/bitrix24")
    if config is not None and "data" in config and "last_export" in config["data"]:
        leads = Lead.query.filter(Lead.last_update >= config["data"]["last_export"]).all()
    else:
        leads = None

    if leads is not None:
        for lead in leads:
            try:
                run_export(local_id=lead.id)
                run_data_efi_export(local_id=lead.id)
                db.session.commit()
                time.sleep(1)
            except Exception as e:
                trace_output = traceback.format_exc()
                print(traceback)

        config = get_config_item("importer/bitrix24")
        if config is not None and "data" in config:
            config["data"]["last_export"] = str(datetime.now())
        update_config_item("importer/bitrix24", config)


def run_full_export():
    print("Full Lead Export")
    leads = Lead.query.filter(and_(Lead.status != "won", Lead.status != "lost")).all()
    for lead in leads:
        run_export(local_id=lead.id)
