from app import db
import pprint
from datetime import datetime, timedelta
from sqlalchemy import and_

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

    if lead.reseller_id is None or lead.reseller_id == 0:
        return None

    reseller_link = find_association("Reseller", local_id=lead.reseller_id)
    customer_link = find_association("Customer", local_id=lead.customer_id)
    #if customer_link is None:
        #run_customer_export(local_id=lead.customer_id)
        #customer_link = find_association("Customer", local_id=lead.customer_id)
        #if customer_link is None:
        #    return None
    status = "NEW"
    if lead.status == "contacted":
        status = "IN_PROCESS"
    if lead.status == "tel_not_connected":
        status = "5"
    if lead.status == "survey_created":
        status = "4"
    if lead.status == "offer_created":
        status = "PROCESSED"
    if lead.status == "offer_presented":
        status = "1"
    if lead.status == "offer_negotiation":
        status = "1"
    if lead.status == "lost":
        status = "JUNK"
    if lead.status == "won":
        status = "CONVERTED"
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
            print(last_space)
            street_nb = street[last_space+1:]
            street = street[0:last_space]
    data = {
        "fields[TITLE]": (("" if lead.customer.company is None else lead.customer.company + " ") + lead.customer.lastname).strip(),
        "fields[COMPANY_TITLE]": lead.customer.company,
        "fields[HONORIFIC]": salutation,
        "fields[NAME]": lead.customer.firstname,
        "fields[LAST_NAME]": lead.customer.lastname,
        "fields[EMAIL][0][TYPE_ID]": "EMAIL",
        "fields[EMAIL][0][VALUE]": lead.customer.email,
        "fields[EMAIL][0][VALUE_TYPE]": "WORK",
        "fields[HAS_EMAIL]": "Y",
        "fields[UF_CRM_5DD4020221169]": street,
        "fields[UF_CRM_5DD402022E300]": street_nb,
        "fields[UF_CRM_5DD4020242167]": lead.customer.default_address.zip,
        "fields[UF_CRM_5DD4020239456]": lead.customer.default_address.city,
        "fields[OPPORTUNITY]": lead.value,
        "fields[STATUS_ID]": status,
        "fields[OPENED]": "Y",
        "email": lead.customer.email
        #"fields[ASSIGNED_BY_ID]": reseller_link.remote_id
    }
    if "Telefon 1" in lead.data:
        data["fields[PHONE]"] = lead.data["Telefon 1"]
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

    if reseller_link is not None:
        data["fields[ASSIGNED_BY_ID]"] = reseller_link.remote_id
    if customer_link is not None:
        data["fields[CONTACT_ID]"] = customer_link.remote_id
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
        print("Lead Export", lead.id)
        post_data = filter_export_input(lead)
        if post_data is not None:
            lead_association = find_association("Lead", local_id=lead.id)
            if lead_association is None:
                response = post("crm.lead.add", post_data=post_data)
                if "result" in response:
                    associate_item(model="Lead", local_id=lead.id, remote_id=response["result"])
                pp = pprint.PrettyPrinter(indent=2)
                pp.pprint(response)
            else:
                post_data["id"] = lead_association.remote_id
                response = post("crm.lead.get", post_data=post_data)
                pp = pprint.PrettyPrinter(indent=2)
                pp.pprint(response)
                if "result" in response and "EMAIL" in response["result"]:
                    for email in response["result"]["EMAIL"]:
                        if email["VALUE"] == post_data["email"]:
                            if "fields[EMAIL][0][TYPE_ID]" in post_data:
                                del post_data["fields[EMAIL][0][TYPE_ID]"]
                            if "fields[EMAIL][0][VALUE]" in post_data:
                                del post_data["fields[EMAIL][0][VALUE]"]
                            if "fields[EMAIL][0][VALUE_TYPE]" in post_data:
                                del post_data["fields[EMAIL][0][VALUE_TYPE]"]
                response = post("crm.lead.update", post_data=post_data)
                pp = pprint.PrettyPrinter(indent=2)
                pp.pprint(response)


def run_cron_export():
    config = get_config_item("importer/bitrix24")
    if config is not None and "data" in config and "last_export" in config["data"]:
        leads = Lead.query.filter(Lead.last_update >= config["data"]["last_export"]).all()
    else:
        leads = None

    if leads is not None:
        for lead in leads:
            run_export(local_id=lead.id)

        config = get_config_item("importer/bitrix24")
        if config is not None and "data" in config:
            config["data"]["last_export"] = str(datetime.now())
        update_config_item("importer/bitrix24", config)


def run_full_export():
    print("Full Lead Export")
    leads = Lead.query.filter(and_(Lead.status != "won", Lead.status != "lost")).all()
    for lead in leads:
        run_export(local_id=lead.id)
