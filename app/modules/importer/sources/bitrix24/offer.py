import pprint
import time
from sqlalchemy import and_
from datetime import datetime, timedelta

from app import db
from app.models import OfferV2
from app.modules.lead.lead_services import add_item, update_item
from app.modules.settings.settings_services import get_one_item as get_config_item, update_item as update_config_item

from ._connector import post, get
from ._association import find_association, associate_item
from .customer import run_export as run_customer_export


def filter_import_input(item_data):
    return None


def filter_export_input(offer: OfferV2):
    config = get_config_item("importer/bitrix24")

    lead_link = find_association("Lead", local_id=offer.lead_id)
    customer_link = find_association("Customer", local_id=offer.customer_id)
    if customer_link is None:
        run_customer_export(local_id=offer.customer_id)
        customer_link = find_association("Customer", local_id=offer.customer_id)
        if customer_link is None:
            return None
    customer_company_link = find_association("CustomerCompany", local_id=offer.customer_id)
    reseller_link = find_association("Reseller", local_id=offer.reseller_id)
    data = {
        'fields[ASSIGNED_BY_ID]': reseller_link.remote_id,
        'fields[CLIENT_ADDR]': '',
        'fields[CLIENT_CONTACT]': (offer.customer.firstname + " " + offer.customer.lastname).strip(),
        'fields[CLIENT_EMAIL]': None,
        'fields[CLIENT_PHONE]': None,
        'fields[CLIENT_TITLE]': '',
        'fields[CONTACT_ID]': customer_link.remote_id,
        'fields[CURRENCY_ID]': 'EUR',
        'fields[LEAD_ID]': lead_link.remote_id,
        'fields[OPPORTUNITY]': offer.total,
        'fields[PERSON_TYPE_ID]': config["data"]["customer_person_type_id"],
        'fields[STATUS_ID]': 'DRAFT',
        "fields[TITLE]": (("" if offer.customer.company is None else offer.customer.company + " ") + offer.customer.lastname).strip(),
        "products": {}
    }
    index = 0
    for item in offer.items:
        product_link = find_association("Product", local_id=item.product_id)
        data["products"]['rows[{}][PRODUCT_ID]'.format(index)] = product_link.remote_id
        data["products"]['rows[{}][PRICE]'.format(index)] = float(item.single_price)
        data["products"]['rows[{}][PRICE_ACCOUNT]'.format(index)] = float(item.single_price)
        data["products"]['rows[{}][PRICE_BRUTTO]'.format(index)] = float(item.total_price)
        data["products"]['rows[{}][PRICE_EXCLUSIVE]'.format(index)] = float(item.total_price)
        data["products"]['rows[{}][PRICE_NETTO]'.format(index)] = float(item.total_price_net)
        data["products"]['rows[{}][QUANTITY]'.format(index)] = float(item.quantity)
        data["products"]['rows[{}][TAX_INCLUDED]'.format(index)] = 'Y'
        data["products"]['rows[{}][TAX_RATE]'.format(index)] = item.tax_rate
        index = index + 1
    if customer_company_link is not None:
        data['fields[COMPANY_ID]'] = customer_company_link.remote_id
        data['fields[PERSON_TYPE_ID]'] = config["data"]["company_person_type_id"]
    return data


def run_import(remote_id=None, local_id=None):
    print("run _import")
    response = post("crm.quote.get", post_data={
        "ID": remote_id
    })
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(response)


def run_export(remote_id=None, local_id=None):
    pp = pprint.PrettyPrinter(indent=2)
    config = get_config_item("importer/bitrix24")

    offer = None
    if remote_id is not None:
        link = find_association("Offer", remote_id=remote_id)
        if link is not None:
            offer = OfferV2.query.filter(OfferV2.id == link.local_id).first()
    if local_id is not None:
        offer = OfferV2.query.filter(OfferV2.id == local_id).first()
    if offer is None:
        return None

    post_data = filter_export_input(offer=offer)
    print("export offer: ", post_data)
    if post_data is not None:
        response = post("crm.quote.add", post_data=post_data)
        if "result" in response:
            post_data["products"]["id"] = response["result"]
            response_rows = post("crm.quote.productrows.set", post_data=post_data["products"])
            response = post("crm.documentgenerator.document.add", post_data={
                "templateId": config["data"]["document_template_id"],
                "entityTypeId": config["data"]["document_offer_id"],
                "entityId": response["result"]
            })
            if "result" in response and "document" in response["result"] and "id" in response["result"]["document"]:
                counter = 0
                while "pdfUrlMachine" not in response["result"]["document"] and counter <= 10:
                    response = post("crm.documentgenerator.document.get", post_data={
                        "id": response["result"]["document"]["id"]
                    })
                    counter = counter + 1
                    time.sleep(5)

        pp.pprint(response)


