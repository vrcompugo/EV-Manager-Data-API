import re
import json
import base64
import datetime
from dateutil.parser import parse
from schwifty import IBAN

from app import db
from app.exceptions import ApiException
from app.models import OfferV2
from app.modules.external.bitrix24.deal import get_deal, get_deals, get_deals_normalized, update_deal, set_default_data
from app.modules.external.bitrix24.contact import get_contact, update_contact
from app.modules.settings import get_settings
from app.utils.ml_stripper import MLStripper

from ._connector import post, put, get
from .customer import export_contact


def get_contract_data_by_deal(deal_id):
    deal = get_deal(deal_id, force_reload=True)
    if deal is None:
        raise ApiException('deal not found', 'Auftrag nicht gefunden')
    if deal.get("category_id") not in ["15", "68", "70", "176", "202"]:
        return {"status": "failed", "data": {"error": "Nur in Cloud Pipeline verfügbar"}, "message": ""}
    if deal.get("category_id") in ["15", "176"]:
        return get_cloud_contract_data_by_deal(deal)
    if deal.get("category_id") == "68":
        return get_service_contract_data_by_deal(deal)
    if deal.get("category_id") == "70":
        return get_insurance_contract_data_by_deal(deal)
    if deal.get("category_id") == "70":
        return get_insurance_contract_data_by_deal(deal)
    if deal.get("category_id") == "202":
        return get_hv_contract_data_by_deal(deal)


def get_hv_contract_data_by_deal(deal):
    from app.modules.importer.sources.bitrix24.order import run_import as order_import
    from app.modules.order.order_services import generate_contract_number

    contract_number = normalize_contract_number(deal.get("contract_number"))
    print(contract_number)
    if contract_number in [None, ""]:
        order = order_import(remote_id=deal["id"])
        if order is None:
            raise ApiException('order import failed', 'Order Import failed')
        contract_number = generate_contract_number(order, number_prefix="")
        if contract_number not in [None, ""]:
            order.contract_number = contract_number
            db.session.commit()
            deal["contract_number"] = contract_number
            update_deal(id=deal["id"], data={
                "contract_number": contract_number
            })
    if contract_number in [None, ""]:
        raise ApiException('contract_number_failed', 'Vertragsnummer konnte nicht erzeugt werden')
    data = load_json_data(deal.get("fakturia_data"))
    if data is None:
        data = initilize_hv_contract_data(deal)
    if data is None:
        raise ApiException('init_failed', 'Initialisierung fehlgeschlagen')
    deal["item_lists"] = data["item_lists"]
    deal["link"] = f"https://keso.bitrix24.de/crm/deal/details/{deal['id']}/"
    delivery_begin = None
    if deal.get("hv_begindate") not in [None, "", "None"]:
        delivery_begin = deal.get("hv_begindate")[0:deal.get("hv_begindate").find("T")]
        deal["sepa_mandate_since"] = delivery_begin
        update_deal(id=deal["id"], data={
            "sepa_mandate_since": delivery_begin
        })
    if len(deal["item_lists"]) > 0:
        deal["item_lists"][0]["start"] = delivery_begin
        deal["item_lists"][0]["items"][0]["deal"]["link"] = deal["link"]
    contact = get_contact(deal["contact_id"], force_reload=True)
    if contact.get("fakturia_iban") in [None, ""]:
        if deal.get("hv_iban") in [None, ""]:
            raise ApiException('missing_iban', 'Iban nicht vorhanden')
        iban = IBAN(deal.get("hv_iban"))
        bic = iban.bic.compact
        iban = iban.compact
        update_contact(contact.get("id"), {
            "fakturia_iban": iban,
            "fakturia_bic": bic
        })
    else:
        iban = contact.get("fakturia_iban")
        bic = contact.get("fakturia_bic")

    deal["fakturia"] = {
        "customer_number": contact.get("fakturia_number"),
        "iban": iban,
        "bic": bic,
        "owner": f"{contact.get('name')} {contact.get('last_name')}",
        "delivery_begin": delivery_begin,
        "contract_number": ""
    }
    if contract_number not in [None, "", "0", 0]:
        deal["fakturia"]["contract_number"] = int(contract_number)
        deal["fakturia"]["invoices"] = get(f"/Invoices", parameters={
            "contractNumber": deal["fakturia"]["contract_number"],
            "extendedData": True
        })
    return deal


def get_insurance_contract_data_by_deal(deal):
    deal = get_service_contract_data_by_deal(deal)
    if "item_lists" in deal:
        if len(deal["item_lists"]) > 0 and deal["item_lists"][0]["items"][0]["type"] != "insurance":
            price = 0
            if 0 <= float(deal.get("pv_kwp")) < 10:
                price = 99
            if 10 <= float(deal.get("pv_kwp")) <= 19:
                price = 149
            if 19 < float(deal.get("pv_kwp")) < 30:
                price = 179
            if 30 <= float(deal.get("pv_kwp")) < 70:
                price = 369
            if 70 <= float(deal.get("pv_kwp")):
                price = float(deal.get("pv_kwp")) * 5.5
            data = {
                "item_lists": [
                    {
                        "start": None,
                        "end": None,
                        "items": [{
                            "type": "insurance",
                            "label": "PV Versicherung",
                            "description": "Contracting Vertrag - Photovoltaik Versicherung",
                            "tax_rate": 19,
                            "total_price": price * 1.19,
                            "total_price_net": price,
                            "deal": {"id": deal["id"], "title": deal["title"]}
                        }]
                    }
                ]
            }
            deal["item_lists"] = data["item_lists"]
            update_deal(deal.get("id"), {
                "fakturia_data": store_json_data(data)
            })
    return deal



def get_service_contract_data_by_deal(deal):
    from app.modules.importer.sources.bitrix24.order import run_import as order_import
    from app.modules.order.order_services import generate_contract_number

    contract_number = normalize_contract_number(deal.get("service_contract_number"))
    if contract_number in [None, ""]:
        order = order_import(remote_id=deal["id"])
        if order is None:
            raise ApiException('order import failed', 'Order Import failed')
        contract_number = generate_contract_number(order, number_prefix="")
        if contract_number not in [None, ""]:
            order.contract_number = contract_number
            db.session.commit()
            deal["service_contract_number"] = contract_number
            update_deal(id=deal["id"], data={
                "service_contract_number": contract_number
            })
    if contract_number in [None, ""]:
        raise ApiException('contract_number_failed', 'Vertragsnummer konnte nicht erzeugt werden')
    data = load_json_data(deal.get("fakturia_data"))
    if data is None:
        data = initilize_service_contract_data(deal)
    if data is None:
        raise ApiException('init_failed', 'Initialisierung fehlgeschlagen')
    deal["item_lists"] = data["item_lists"]
    deal["link"] = f"https://keso.bitrix24.de/crm/deal/details/{deal['id']}/"
    delivery_begin = None
    if deal.get("activation_date") not in [None, "", "None"]:
        delivery_begin = deal.get("activation_date")[0:deal.get("activation_date").find("T")]
        deal["sepa_mandate_since"] = delivery_begin
        update_deal(id=deal["id"], data={
            "sepa_mandate_since": delivery_begin
        })
        delivery_begin = datetime.datetime.strptime(delivery_begin, "%Y-%m-%d")
        year = delivery_begin.year + 1
        delivery_begin = str(year) + delivery_begin.strftime("-%m-%d")
    if len(deal["item_lists"]) > 0:
        deal["item_lists"][0]["start"] = delivery_begin
        deal["item_lists"][0]["items"][0]["deal"]["link"] = deal["link"]
    contact = get_contact(deal["contact_id"])
    if deal.get("iban") not in [None]:
        iban = deal.get("iban").replace(" ", "")
    if deal.get("bic") not in [None]:
        bic = deal.get("bic").replace(" ", "")

    deal["fakturia"] = {
        "customer_number": contact.get("fakturia_number"),
        "iban": iban,
        "bic": bic,
        "owner": f"{contact.get('name')} {contact.get('last_name')}",
        "delivery_begin": delivery_begin,
        "contract_number": ""
    }
    if contract_number not in [None, "", "0", 0]:
        deal["fakturia"]["contract_number"] = int(contract_number)
        deal["fakturia"]["invoices"] = get(f"/Invoices", parameters={
            "contractNumber": deal["fakturia"]["contract_number"],
            "extendedData": True
        })
    return deal


def initilize_hv_contract_data(deal):
    total_price_net = 25
    total_price = total_price_net * 1.19
    data = {
        "item_lists": [
            {
                "start": None,
                "end": None,
                "items": [{
                    "type": "hv-vertrag",
                    "label": "HV Vertrag",
                    "description": "",
                    "tax_rate": 19,
                    "total_price": total_price,
                    "total_price_net": total_price_net,
                    "deal": {"id": deal["id"], "title": deal["title"]}
                }]
            }
        ]
    }
    update_deal(deal.get("id"), {
        "fakturia_data": store_json_data(data)
    })
    return data


def initilize_service_contract_data(deal):
    total_price = 72 * 1.19
    total_price_net = 72
    if deal["contracting_version"] == "Version G1":
        total_price = 84 * 1.19
        total_price_net = 84
    data = {
        "item_lists": [
            {
                "start": None,
                "end": None,
                "items": [{
                    "type": "service",
                    "label": "Remote Care Jahres Beitrag",
                    "description": "Contracting Vertrag\n - Remote Care - Online Überwachung PV Anlage",
                    "tax_rate": 19,
                    "total_price": total_price,
                    "total_price_net": total_price_net,
                    "deal": {"id": deal["id"], "title": deal["title"]}
                }]
            }
        ]
    }
    update_deal(deal.get("id"), {
        "fakturia_data": store_json_data(data)
    })
    return data


def get_cloud_contract_data_by_deal(deal):
    cloud_contract_number = normalize_contract_number(deal.get("cloud_contract_number"))
    deal = set_default_data(deal)
    if deal is None:
        return {"status": "failed", "data": {"error": "Cloud Nummer konnten nicht gefunden werden"}, "message": ""}
    if deal.get("category_id") in ["176"]:
        master_deal = get_deals_normalized({
            "category_id": 15,
            "cloud_contract_number": f'{cloud_contract_number}',
            "is_cloud_master_deal": 1
        })
        if master_deal is not None and len(master_deal) > 0:
            deal = master_deal[0]

    if deal.get("is_cloud_master_deal") == "1" and deal.get("fakturia_data") not in [None, ""]:
        data = load_json_data(deal.get("fakturia_data"))
    else:
        if cloud_contract_number in [None, ""]:
            return deal
        master_deal = get_deals_normalized({
            "category_id": 15,
            "cloud_contract_number": f'{cloud_contract_number}',
            "is_cloud_master_deal": 1
        })
        if master_deal is not None and len(master_deal) > 0:
            deal = master_deal[0]
            data = load_json_data(deal.get("fakturia_data"))
            if data is None:
                data = initilize_faktura_data(master_deal[0])
        else:
            deals = get_deals_normalized({
                "category_id": 15,
                "cloud_contract_number": f'{cloud_contract_number}'
            })
            maindeal = None
            for subdeal in deals:
                if _is_lightcloud_deal(subdeal):
                    if maindeal is not None:
                        maindeal = None
                        break
                    maindeal = subdeal
            if maindeal is not None:
                update_deal(maindeal.get("id"), {
                    "is_cloud_master_deal": 1
                })
                deal = maindeal
                data = initilize_faktura_data(maindeal)
            else:
                return {"deals": deals}
    if data is None:
        return {"status": "failed", "data": {"error": "Vertragsdaten konnten nicht gefunden werden"}, "message": ""}
    delivery_begin = None
    if deal.get("cloud_delivery_begin") not in [None, "", "None"]:
        delivery_begin = deal.get("cloud_delivery_begin")[0:deal.get("cloud_delivery_begin").find("T")]
    if "items" in data:
        data["item_lists"] = [
            {
                "start": delivery_begin,
                "end": None,
                "items": data["items"]
            }
        ]
    deal["item_lists"] = data["item_lists"]
    deal["link"] = f"https://keso.bitrix24.de/crm/deal/details/{deal['id']}/"
    deal["cloud_contract_number"] = cloud_contract_number
    if cloud_contract_number in [None, ""]:
        unassigend_deals = []
    else:
        unassigend_deals = get_deals_normalized({
            "category_id": 15,
            "cloud_contract_number": f'{cloud_contract_number}'
        })
    for index, unassigend_deal in enumerate(unassigend_deals):
        unassigend_deals[index]["link"] = f"https://keso.bitrix24.de/crm/deal/details/{unassigend_deal['id']}/"
    if len(deal["item_lists"]) > 0:
        deal["item_lists"][0]["start"] = delivery_begin
    for list in deal["item_lists"]:
        for item in list["items"]:
            deal_index = next((index for (index, subdeal) in enumerate(unassigend_deals) if item.get("deal") is not None and subdeal["id"] == item["deal"]["id"]), None)
            if deal_index is not None:
                item["deal"]["link"] = unassigend_deals[deal_index]['link']
                del unassigend_deals[deal_index]
    deal["unassigend_deals"] = unassigend_deals
    contact = get_contact(deal["contact_id"])
    if deal.get("iban") not in [None]:
        iban = deal.get("iban").replace(" ", "")
    if deal.get("bic") not in [None]:
        bic = deal.get("bic").replace(" ", "")
    deal["fakturia"] = {
        "customer_number": contact.get("fakturia_number"),
        "iban": iban,
        "bic": bic,
        "owner": f"{contact.get('name')} {contact.get('last_name')}",
        "delivery_begin": delivery_begin,
        "contract_number": ""
    }
    if cloud_contract_number not in [None, "", "0", 0]:
        deal["fakturia"]["contract_number"] = int(cloud_contract_number.replace("C", ""))
        deal["fakturia"]["invoices"] = get(f"/Invoices", parameters={
            "contractNumber": deal["fakturia"]["contract_number"],
            "extendedData": True
        })
    deal["fakturia"]["items_to_update"] = []
    return deal

def get_contract(contract_number):
    contract_number = int(contract_number.replace("C", ""))
    data = get(f"/Contracts/{contract_number}", parameters={
        "extendedData": True
    })
    if len(data.keys()) == 0:
        return None
    return data

def get_payments(contract_number):
    contract_number = int(contract_number.replace("C", ""))
    invoices = get(f"/Invoices", parameters={
        "contractNumber": contract_number,
        "extendedData": True
    })
    invoice_correntions = get(f"/InvoiceCorrections", parameters={
        "contractNumber": contract_number,
        "extendedData": True
    })
    credit_notes = get(f"/CreditNotes", parameters={
        "contractNumber": contract_number,
        "extendedData": True
    })
    credit_note_correntions = get(f"/CreditNoteCorrections", parameters={
        "contractNumber": contract_number,
        "extendedData": True
    })
    data = []
    for item in invoices:
        data.append(enhance_payment(item, "invoice"))
    for item in invoice_correntions:
        data.append(enhance_payment(item, "invoice_corrention"))
    for item in credit_notes:
        data.append(enhance_payment(item, "credit_note"))
    for item in credit_note_correntions:
        data.append(enhance_payment(item, "credit_note_corrention"))
    data = sorted(data, key=lambda d: d['date'])
    for item in data:
        item["date"] = str(item["date"])
    return data


def enhance_payment(item, item_type):
    item["date"] = parse(item["date"])
    item["type"] = item_type
    item["service_year"] = {}
    item["service_year_net"] = {}
    if item.get("payItems") is not None:
        for pay_item in item["payItems"]:
            item["service_year_net"][pay_item["performanceDateStart"][:4]] = pay_item["amountNetSum"]
            item["service_year"][pay_item["performanceDateStart"][:4]] = pay_item["amountNetSum"] * (1 + (pay_item["taxRatePercent"] / 100))
    item["amountGross_normalized"] = item["amountGross"]
    if item_type in ["credit_note"]:
        item["amountGross_normalized"] = item["amountGross"] * -1
    return item


def get_payments2(account_number):
    data = get(f"/Accounts/{account_number}/Transactions", parameters={
        "extendedData": True
    })
    return data


def initilize_faktura_data(deal):
    print("init")
    cloud_contract_number = normalize_contract_number(deal.get("cloud_contract_number"))
    delivery_begin = None
    if deal.get("cloud_delivery_begin") not in [None, "", "None"]:
        delivery_begin = deal.get("cloud_delivery_begin")[0:deal.get("cloud_delivery_begin").find("T")]
    data = deal
    data["cloud_contract_number"] = cloud_contract_number
    data["item_lists"] = [
        {
            "start": delivery_begin,
            "end": None,
            "items": []
        }
    ]
    unassigend_deals = get_deals_normalized({
        "category_id": 15,
        "cloud_contract_number": f'{cloud_contract_number}'
    })
    offer = OfferV2.query.options(db.subqueryload("items")).filter(OfferV2.number == deal.get("cloud_number")).first()
    if offer is not None:
        for item in offer.items:
            item_data = {
                "type": "text",
                "label": item.label,
                "description": item.description,
                "tax_rate": int(item.tax_rate),
                "total_price": float(item.total_price),
                "total_price_net": float(item.total_price_net),
                "deal": None
            }
            deal_index = None
            if item.label in ["BSH-Cloud", "cCloud-Zero", "EEG-Cloud"]:
                deal_index = next((index for (index, subdeal) in enumerate(unassigend_deals) if _is_lightcloud_deal(subdeal)), None)
                item_data["type"] = "lightcloud"
                item_data["usage"] = float(deal.get("lightcloud_usage")) if deal.get("lightcloud_usage") not in [None, ""] else None
            if item.description[:17] == "<b>Wärmecloud</b>":
                deal_index = next((index for (index, subdeal) in enumerate(unassigend_deals) if _is_heatcloud_deal(subdeal)), None)
                item_data["type"] = "heatcloud"
                item_data["usage"] = float(deal.get("heatcloud_usage")) if deal.get("heatcloud_usage") not in [None, ""] else None
            if item.description[:13] == "<b>eCloud</b>":
                deal_index = next((index for (index, subdeal) in enumerate(unassigend_deals) if _is_ecloud_deal(subdeal)), None)
                item_data["type"] = "ecloud"
                item_data["usage"] = float(deal.get("ecloud_usage")) if deal.get("ecloud_usage") not in [None, ""] else None
            if item.description[:15] == "<b>Consumer</b>":
                deal_index = next((index for (index, subdeal) in enumerate(unassigend_deals) if _is_consumer_deal(subdeal)), None)
                item_data["type"] = "consumer"
            if item.description[:12] == "<b>eMove</b>":
                deal_index = next((index for (index, subdeal) in enumerate(unassigend_deals) if _is_consumer_deal(subdeal)), None)
                item_data["type"] = "emove"
                if item.description.find("emove.drive I") >= 0:
                    item_data["usage"] = 500
                    item_data["usage_outside"] = 1000
                if item.description.find("emove.drive II") >= 0:
                    item_data["usage"] = 1000
                    item_data["usage_outside"] = 1000
                if item.description.find("emove.drive III") >= 0:
                    item_data["usage"] = 2000
                    item_data["usage_outside"] = 3000
                if item.description.find("emove.drive ALL") >= 0:
                    item_data["usage"] = 2500
                    item_data["usage_outside"] = 6000
            if deal_index is not None:
                item_data["deal"] = unassigend_deals[deal_index]
                del unassigend_deals[deal_index]

            data["item_lists"][0]["items"].append(item_data)
    else:
        pass
    data["unassigend_deals"] = unassigend_deals
    update_deal(deal.get("id"), {
        "fakturia_data": store_json_data({"item_lists": data["item_lists"]})
    })
    return data


def add_item_list(deal_id, newData):
    data = get_contract_data_by_deal(deal_id)
    if "newItemsList" not in newData:
        print("no list")
        raise ApiException('newItemsList_not_found', 'Produktliste nicht gefunden')
    last_start = None
    new_start = None
    if newData["newItemsList"].get("start") not in [None, "", "0000-00-00"]:
        new_start = datetime.datetime.strptime(newData["newItemsList"].get("start"), '%Y-%m-%d')
    last_list = None
    if len(data["item_lists"]) > 0:
        last_list = data["item_lists"][len(data["item_lists"]) - 1]
    if last_list is not None and last_list.get("start") not in [None, "", "0000-00-00"]:
        last_start = datetime.datetime.strptime(last_list.get("start"), '%Y-%m-%d')
    if last_start is None:
        if "fakturia" in newData and "delivery_begin" in newData["fakturia"] and newData["fakturia"]["delivery_begin"] not in [None, "None", ""]:
            last_start = datetime.datetime.strptime(newData["fakturia"]["delivery_begin"], '%Y-%m-%d')
    if new_start is not None:
        if new_start < datetime.datetime.now():
            raise ApiException('newItemsList_not_found', 'Startdatum muss neuer sein als das aktuelle Datum')
        if last_start is not None and new_start < last_start:
            raise ApiException('newItemsList_not_found', 'Startdatum muss neuer sein als das letzte Startdatum')
    if new_start is None and len(data["item_lists"]) == 1:
        if last_start is not None and last_start < datetime.datetime.now() and data.get("fakturia_contract_number") not in [None, "", "0"]:
            raise ApiException('newItemsList_not_found', 'Startdatum muss neuer sein als das letzte Startdatum')
        data["item_lists"][0] = {
            "start": new_start,
            "items": newData["newItemsList"].get("items")
        }
    else:
        new_start = new_start.strftime('%Y-%m-%d')
        data["item_lists"].append({
            "start": new_start,
            "items": newData["newItemsList"].get("items")
        })
    update_deal(deal_id, {
        "fakturia_data": store_json_data({"item_lists": data["item_lists"]})
    })
    return data


def delete_item_list(deal_id, list_index):
    list_index = int(list_index)
    data = get_contract_data_by_deal(deal_id)
    if data["item_lists"][list_index].get("start") not in [None, "None", "0", 0]:
        start = datetime.datetime.strptime(data["item_lists"][list_index].get("start"), '%Y-%m-%d')
        if start < datetime.datetime.now():
            return data
    del data["item_lists"][list_index]
    update_deal(deal_id, {
        "fakturia_data": store_json_data({"item_lists": data["item_lists"]})
    })
    return data


def update_item_list_item(deal_id, list_index, index, inputData):
    list_index = int(list_index)
    index = int(index)
    data = get_contract_data_by_deal(deal_id)
    data["item_lists"][list_index]["items"][index]["usage"] = inputData.get("newUsage")
    data["item_lists"][list_index]["items"][index]["usage_outside"] = inputData.get("newUsageOutside")
    update_deal(deal_id, {
        "fakturia_data": store_json_data({"item_lists": data["item_lists"]})
    })
    return data


def assign_subdeal_to_item(deal_id, list_index, item_index, subdeal_id):
    list_index = int(list_index)
    item_index = int(item_index)
    deal = get_deal(deal_id)
    if str(deal.get("is_cloud_master_deal")) != "1":
        raise ApiException('not-master', 'Aktueller Auftrag ist nicht der Hauptauftrag')
    data = load_json_data(deal.get("fakturia_data"))
    if "item_lists" not in data or len(data["item_lists"]) <= list_index:
        raise ApiException('no-item', 'Keine Produktliste definiert')
    subdeal = get_deal(subdeal_id)
    if subdeal is None:
        raise ApiException('subdeal_not_found', 'Unterauftrag nicht gefunden')
    if data["item_lists"][list_index]["items"][item_index]["type"] == "lightcloud":
        update_deal(subdeal.get("id"), {
            "is_cloud_consumer": "0",
            "is_cloud_ecloud": "0",
            "is_cloud_heatcloud": "0",
            "cloud_type": ["Zero"]
        })
    if data["item_lists"][list_index]["items"][item_index]["type"] == "consumer":
        update_deal(subdeal.get("id"), {
            "is_cloud_consumer": "1",
            "is_cloud_ecloud": "0",
            "is_cloud_heatcloud": "0",
            "cloud_type": ["Consumer"]
        })
    if data["item_lists"][list_index]["items"][item_index]["type"] == "heatcloud":
        update_deal(subdeal.get("id"), {
            "is_cloud_consumer": "1",
            "is_cloud_ecloud": "0",
            "is_cloud_heatcloud": "1",
            "cloud_type": ["Wärmecloud"]
        })
    if data["item_lists"][list_index]["items"][item_index]["type"] == "ecloud":
        update_deal(subdeal.get("id"), {
            "is_cloud_consumer": "0",
            "is_cloud_ecloud": "1",
            "is_cloud_heatcloud": "0",
            "cloud_type": ["eCloud"]
        })
    data["item_lists"][list_index]["items"][item_index]["deal"] = subdeal
    update_deal(deal.get("id"), {
        "fakturia_data": store_json_data(data)
    })
    return True


def load_json_data(field_data):
    if field_data in [None, "", "0", 0]:
        return None
    return json.loads(base64.b64decode(field_data.encode('utf-8')).decode('utf-8'))


def store_json_data(data):
    return base64.b64encode(json.dumps(data).encode('utf-8')).decode('utf-8')


def normalize_contract_number(cloud_contract_number):
    if cloud_contract_number in [None, "None", "", 0, "0"]:
        return None
    number = re.findall(r'C[0-9]+', cloud_contract_number)
    if len(number) > 0:
        return number[0]
    return cloud_contract_number


def _is_lightcloud_deal(deal):
    return str(deal.get("is_cloud_consumer")) in ["None", "0"] and \
        str(deal.get("is_cloud_ecloud")) in ["None", "0"] and \
        str(deal.get("is_cloud_heatcloud")) in ["None", "0"] and \
        len(deal.get("cloud_type", [])) > 0 and deal.get("cloud_type", [])[0] == "Zero"


def _is_heatcloud_deal(deal):
    return str(deal.get("is_cloud_ecloud")) in ["None", "0"] and \
        str(deal.get("is_cloud_heatcloud")) == "1" and \
        len(deal.get("cloud_type", [])) > 0 and "Wärmecloud" in deal.get("cloud_type", [])


def _is_ecloud_deal(deal):
    return str(deal.get("is_cloud_ecloud")) == "1" and \
        str(deal.get("is_cloud_heatcloud")) in ["None", "0"] and \
        len(deal.get("cloud_type", [])) > 0 and "eCloud" in deal.get("cloud_type", [])


def _is_consumer_deal(deal):
    return str(deal.get("is_cloud_consumer")) == "1" and \
        str(deal.get("is_cloud_ecloud")) in ["None", "0"] and \
        str(deal.get("is_cloud_heatcloud")) in ["None", "0"] and \
        len(deal.get("cloud_type", [])) > 0 and "Consumer" in deal.get("cloud_type", [])


def get_export_data(deal, contact):
    if deal["category_id"] == "15":
        return get_export_data_cloud(deal, contact)
    if deal["category_id"] == "68":
        return get_export_data_service(deal, contact)
    if deal["category_id"] == "70":
        return get_export_data_insurance(deal, contact)
    if deal["category_id"] == "202":
        return get_export_data_hv(deal, contact)
    return None, None, None


def get_export_data_hv(deal, contact):
    config = get_settings("external/fakturia")
    subscriptionItemsPrices = []
    subscriptionItems = []
    for item_list in deal.get("item_lists"):
        for item in item_list["items"]:
            if item_list["start"] in [None, "", "0000-00-00"]:
                item_list["start"] = deal["fakturia"].get("delivery_begin")
            item_data = {
                "itemNumber": "hv-vertrag",
                "quantity": 1,
                "extraDescription": "",
                "description": "",
                "unit": "YEAR",
                "validFrom": item_list["start"],
                "ccQuantityChange": False,
                "status": "ACTIVE",
                "activityType": "DEFAULT_PERFORMANCE"
            }
            cost = round(float(item["total_price"]) / 1.19, 4)
            subscriptionItemsPrices.append({
                "cost": cost,
                "currency": "EUR",
                "validFrom": "",
                "minimumQuantity": 1
            })
            subscriptionItems.append(item_data)
    data = {
        "customerNumber": contact.get("fakturia_number"),
        "projectName": "HV Verträge",
        "subscription": {
            "termPeriod": 1,
            "termUnit": "MONTH",
            "noticePeriod": 0,
            "noticeUnit": "DAY",
            "continuePeriod": 0,
            "continueUnit": "DAY",
            "billedInAdvance": True,
            "subscriptionItems": subscriptionItems,
            "status": "ACTIVE"
        },
        "contractNumber": deal["fakturia"].get("contract_number"),
        "name": deal["fakturia"].get("contract_number"),
        "issueDate": deal["fakturia"].get("delivery_begin"),
        "recur": 1,
        "recurUnit": "MONTH",
        "duePeriod": 0,
        "dueUnit": "DAY",
        "paymentMethod": "SEPA_DEBIT",
        "contractStatus": "ACTIVE",
        "trialPeriod": 0,
        "trialUnit": "DAY",
        "trialPeriodEndAction": "CONTINUE",
        "hasTrialperiod": False,
        "ccDisallowTermination": True,
        "taxConfig": "APPLY_ALWAYS",
        "documentDeliveryMode": "EMAIL"
    }
    issue_date = datetime.datetime.strptime(data["issueDate"], '%Y-%m-%d')
    if issue_date.day > 15:
        next_billing_date = issue_date + datetime.timedelta(days=20)
        data["issueDate"] = next_billing_date.strftime("%Y-%m-01")
    else:
        if issue_date.day == 1:
            data["issueDate"] = issue_date.strftime("%Y-%m-01")
        else:
            data["issueDate"] = issue_date.strftime("%Y-%m-15")
    return data, subscriptionItemsPrices, config.get("api-key-contracting")


def get_export_data_insurance(deal, contact):
    data, subscriptionItemsPrices, api_key = get_export_data_service(deal, contact)
    return data, subscriptionItemsPrices, api_key


def get_export_data_service(deal, contact):
    config = get_settings("external/fakturia")
    subscriptionItemsPrices = []
    subscriptionItems = []
    for item_list in deal.get("item_lists"):
        for item in item_list["items"]:
            if item_list["start"] in [None, "", "0000-00-00"]:
                item_list["start"] = deal["fakturia"].get("delivery_begin")
            item_data = {
                "quantity": 1,
                "extraDescription": "",
                "description": "",
                "unit": "YEAR",
                "validFrom": item_list["start"],
                "ccQuantityChange": False,
                "status": "ACTIVE",
                "activityType": "DEFAULT_PERFORMANCE"
            }
            if item["type"] == "service":
                if deal["contracting_version"] == "Version G1":
                    item_data["itemNumber"] = "CV-RC 00122021"
                else:
                    item_data["itemNumber"] = "CV-RC 00092021"
            if item["type"] == "insurance":
                item_data["itemNumber"] = "CV-0092020"
                cost = round(float(item["total_price"]) / 1.19, 4)
                subscriptionItemsPrices.append({
                    "cost": cost,
                    "currency": "EUR",
                    "validFrom": "",
                    "minimumQuantity": 1
                })
            subscriptionItems.append(item_data)
    data = {
        "customerNumber": contact.get("fakturia_number"),
        "projectName": "Contracting Vertrag PV",
        "subscription": {
            "termPeriod": 1,
            "termUnit": "YEAR",
            "noticePeriod": 0,
            "noticeUnit": "DAY",
            "continuePeriod": 0,
            "continueUnit": "DAY",
            "billedInAdvance": True,
            "subscriptionItems": subscriptionItems,
            "status": "ACTIVE"
        },
        "contractNumber": deal["fakturia"].get("contract_number"),
        "name": deal["fakturia"].get("contract_number"),
        "issueDate": deal["fakturia"].get("delivery_begin"),
        "recur": 1,
        "recurUnit": "YEAR",
        "duePeriod": 0,
        "dueUnit": "DAY",
        "paymentMethod": "SEPA_DEBIT",
        "contractStatus": "ACTIVE",
        "trialPeriod": 0,
        "trialUnit": "DAY",
        "trialPeriodEndAction": "CONTINUE",
        "hasTrialperiod": False,
        "ccDisallowTermination": True,
        "taxConfig": "APPLY_ALWAYS",
        "documentDeliveryMode": "EMAIL"
    }
    issue_date = datetime.datetime.strptime(data["issueDate"], '%Y-%m-%d')
    if issue_date.day > 15:
        next_billing_date = issue_date + datetime.timedelta(days=20)
        data["issueDate"] = next_billing_date.strftime("%Y-%m-01")
    else:
        if issue_date.day == 1:
            data["issueDate"] = issue_date.strftime("%Y-%m-01")
        else:
            data["issueDate"] = issue_date.strftime("%Y-%m-15")
    return data, subscriptionItemsPrices, config.get("api-key-contracting")


def get_export_data_cloud(deal, contact):
    is_negative = False
    subscriptionItems = []
    subscriptionItemsPrices = []
    for index, item_list in  enumerate(deal.get("item_lists")):
        item_list["sum"] = 0
        for item in item_list["items"]:
            item_list["sum"] = item_list["sum"] + float(item["total_price"])
        item_data = {
            "itemNumber": "vorauszahlung",
            "quantity": 1,
            "extraDescription": f"für Vertrag: {deal.get('cloud_contract_number')}",
            "description": "",
            "unit": "MONTH",
            "validFrom": item_list["start"],
            "ccQuantityChange": False,
            "status": "ACTIVE",
            "activityType": "DEFAULT_PERFORMANCE"
        }
        if index < len(deal.get("item_lists")) - 1:
            item_data["validTo"] = deal.get("item_lists")[index + 1]["start"]
        cost = round(item_list["sum"] / 1.19, 4)
        if cost < 0:
            item_data["activityType"] = "REVERSE_PERFORMANCE_OTHER"
            cost = cost * -1
            is_negative = True
        subscriptionItemsPrices.append({
            "cost": cost,
            "currency": "EUR",
            "validFrom": "",
            "minimumQuantity": 1
        })
        subscriptionItems.append(item_data)
    data = {
        "customerNumber": contact.get("fakturia_number"),
        "projectName": "Cloud Verträge",
        "subscription": {
            "termPeriod": 1,
            "termUnit": "MONTH",
            "noticePeriod": 0,
            "noticeUnit": "DAY",
            "continuePeriod": 0,
            "continueUnit": "DAY",
            "billedInAdvance": True,
            "subscriptionItems": subscriptionItems,
            "status": "ACTIVE"
        },
        "contractNumber": deal["fakturia"].get("contract_number"),
        "name": deal.get("cloud_contract_number"),
        "issueDate": deal["fakturia"].get("delivery_begin"),
        "recur": 1,
        "recurUnit": "MONTH",
        "duePeriod": 0,
        "dueUnit": "DAY",
        "paymentMethod": "BANKTRANSFER" if is_negative else "SEPA_DEBIT",
        "contractStatus": "ACTIVE",
        "trialPeriod": 0,
        "trialUnit": "DAY",
        "trialPeriodEndAction": "CONTINUE",
        "hasTrialperiod": False,
        "ccDisallowTermination": True,
        "taxConfig": "APPLY_ALWAYS",
        "documentDeliveryMode": "EMAIL"
    }
    issue_date = datetime.datetime.strptime(data["issueDate"], '%Y-%m-%d')
    if issue_date.day > 15:
        next_billing_date = issue_date + datetime.timedelta(days=20)
        data["issueDate"] = next_billing_date.strftime("%Y-%m-01")
    else:
        if issue_date.day == 1:
            data["issueDate"] = issue_date.strftime("%Y-%m-01")
        else:
            data["issueDate"] = issue_date.strftime("%Y-%m-15")
    return data, subscriptionItemsPrices, None


def export_deal(deal_id):
    print("export deal:", deal_id)
    deal = get_contract_data_by_deal(deal_id)
    contact = get_contact(deal.get("contact_id"))
    if contact.get("fakturia_number") in ["", None, "0", 0]:
        export_contact(contact, force=True)
        contact = get_contact(deal.get("contact_id"))
    if contact.get("fakturia_number") in ["", None, "0", 0]:
        print(contact["id"], "no customer number")
        raise ApiException('no-customer', 'Kunde nicht bei Fakturia registriert')
    if contact.get("fakturia_iban") in [None, "None", ""]:
        update_contact(contact["id"], {
            "fakturia_iban": deal["fakturia"]["iban"],
            "fakturia_bic": deal["fakturia"]["bic"],
            "fakturia_owner": deal["fakturia"]["owner"],
        })
        contact["fakturia_iban"] = deal["fakturia"]["iban"]
        contact["fakturia_bic"] = deal["fakturia"]["bic"]
        contact["fakturia_owner"] = deal["fakturia"]["owner"]
    if deal.get("sepa_mandate_since") in [None, "None", ""]:
        raise ApiException('wrong-sepa', 'SEPA Mandatsdatum fehlt')
    if contact.get("sepa_mandate_since") in [None, "None", ""]:
        update_contact(contact["id"], {
            "sepa_mandate_since": deal.get("sepa_mandate_since")
        })
        contact["sepa_mandate_since"] = deal.get("sepa_mandate_since")
    if contact.get("fakturia_iban") != deal["fakturia"]["iban"]:
        if str(contact["id"]) == "49784":
            return
        print(contact["id"], "customer wrong iban", contact.get("fakturia_iban"), deal["fakturia"]["iban"])
        raise ApiException('wrong-iban', 'Kunden IBAN stimmt nicht mit Auftrags IBAN übrein')
    export_contact(contact, force=True)
    export_data, subscriptionItemsPrices, api_key = get_export_data(deal, contact)
    print("asd", json.dumps(export_data, indent=2))
    if export_data is not None:
        contract_data = None
        if deal.get("fakturia_contract_number") in ["", None, 0, "0"]:
            contract_data = post(f"/Contracts", post_data=export_data, token=api_key)
            if contract_data is not None and "contractNumber" in contract_data:
                deal["fakturia_contract_number"] = contract_data["contractNumber"]
                update_deal(deal_id, {
                    "fakturia_contract_number": contract_data["contractNumber"]
                })
                for index, item in enumerate(contract_data.get("subscription").get("subscriptionItems")):
                    if len(subscriptionItemsPrices) > index:
                        response_item = post(f"/Contracts/{deal.get('fakturia_contract_number')}/Subscription/SubscriptionItems/{item.get('uuid')}/customPrices", post_data=subscriptionItemsPrices[index], token=api_key)
                        print(json.dumps(response_item, indent=2))
            else:
                print("contract error", json.dumps(export_data, indent=2), json.dumps(contract_data, indent=2))
                raise ApiException('fakturia-error', 'Fehler beim Übertragen an Fakturia', data={"export_data": export_data, "response": contract_data})
        else:
            contract_data = put(f"/Contracts/{deal.get('fakturia_contract_number')}", post_data=export_data, token=api_key)
            if contract_data is not None and "contractNumber" in contract_data:
                for index, item in enumerate(export_data.get("subscription").get("subscriptionItems")):
                    if len(contract_data.get("subscription").get("subscriptionItems")) <= index:
                        response_item = post(f"/Contracts/{deal.get('fakturia_contract_number')}/Subscription/SubscriptionItems", post_data=item, token=api_key)
                        print(json.dumps(response_item, indent=2))
                        if len(subscriptionItemsPrices) > index:
                            response_item = post(f"/Contracts/{deal.get('fakturia_contract_number')}/Subscription/SubscriptionItems/{contract_data.get('subscription').get('subscriptionItems')[index].get('uuid')}/customPrices", post_data=subscriptionItemsPrices[index], token=api_key)
                            print(json.dumps(response_item, indent=2))
                    else:
                        print(item)
                        response_item = put(f"/Contracts/{deal.get('fakturia_contract_number')}/Subscription/SubscriptionItems/{contract_data.get('subscription').get('subscriptionItems')[index].get('uuid')}", post_data=item, token=api_key)
                        print(json.dumps(response_item, indent=2))

        if contract_data is not None and contract_data.get("contractStatus") == "DRAFT":
            response_activation = post(f"/Contracts/{deal.get('fakturia_contract_number')}/activate")
            print(json.dumps(response_activation, indent=2))
    return deal


def run_cron_export():
    deals = get_deals({
        "FILTER[CATEGORY_ID]": 70,
        "FILTER[STAGE_ID]": "C70:3",
        "SELECT": "full"
    }, force_reload=True)
    if deals is None:
        print("deals could not be loaded")
        return
    for deal in deals:
        if deal.get("iban") not in [None, "", "None"]:
            contracting_deals = get_deals({
                "FILTER[CATEGORY_ID]": 68,
                "FILTER[STAGE_ID]": "C68:NEW",
                "FILTER[UF_CRM_5FA43F983EBAB]": deal.get("unique_identifier"),
                "SELECT": "full"
            })
            if len(contracting_deals) > 0:
                if contracting_deals[0].get("iban") in [None, "", "None"]:
                    update_deal(contracting_deals[0]["id"], {
                        "iban": deal.get("iban"),
                        "bic": deal.get("bic"),
                        "bank": deal.get("bank")
                    })
            if deal.get("fakturia_contract_number") in [None, "", "None"]:
                try:
                    export_deal(deal["id"])
                except Exception as e:
                    continue
                deal = get_deal(deal["id"], force_reload=True)
        if deal.get("fakturia_contract_number") not in [None, "", "None"]:
            print(deal.get("fakturia_contract_number"))
            update_deal(deal["id"], {
                "stage_id": "C70:7"
            })
    deals = get_deals({
        "FILTER[CATEGORY_ID]": "68",
        "FILTER[STAGE_ID]": "C68:NEW",
        "SELECT": "full"
    }, force_reload=True)
    for deal in deals:
        if deal.get("iban") not in [None, "", "None"]:
            if deal.get("fakturia_contract_number") in [None, "", "None"]:
                try:
                    export_deal(deal["id"])
                except Exception as e:
                    continue
                deal = get_deal(deal["id"], force_reload=True)
        if deal.get("fakturia_contract_number") not in [None, "", "None"]:
            print(deal.get("fakturia_contract_number"))
            update_deal(deal["id"], {
                "stage_id": "C68:PREPARATION"
            })
    deals = get_deals({
        "FILTER[CATEGORY_ID]": "202",
        "FILTER[STAGE_ID]": "C202:NEW",
        "SELECT": "full"
    }, force_reload=True)
    for deal in deals:
        if deal.get("hv_iban") not in [None, "", "None"]:
            if deal.get("fakturia_contract_number") in [None, "", "None"]:
                try:
                    export_deal(deal["id"])
                except Exception as e:
                    print(e)
                    continue
                deal = get_deal(deal["id"], force_reload=True)
        if deal.get("fakturia_contract_number") not in [None, "", "None"]:
            print(deal.get("fakturia_contract_number"))
            update_deal(deal["id"], {
                "stage_id": "C202:PREPARATION"
            })


def run_export_by_id(deal_id):
    export_deal(deal_id)
    deal = get_deal(deal_id, force_reload=True)
    if deal.get("fakturia_contract_number") not in [None, "", "None"]:
        print(deal.get("fakturia_contract_number"))
        update_deal(deal["id"], {
            "stage_id": "C202:PREPARATION"
        })

