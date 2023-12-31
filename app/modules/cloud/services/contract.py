import datetime
from tkinter import N
from turtle import update
import pytz
import re
import json
import calendar
import math
import time
import copy
from dateutil.parser import parse
from calendar import monthrange

from app import db
from app.modules.cloud.models.counter_value import CounterValue
from app.utils.model_func import to_dict
from app.utils.set_attr_by_dict import set_attr_by_dict
from app.modules.settings import get_settings
from app.modules.external.bitrix24.deal import get_deals, get_deal, update_deal, delete_deal
from app.modules.external.bitrix24.contact import get_contact
from app.modules.external.fakturia.deal import get_payments, get_payments2, get_contract
from app.modules.external.fakturia.activity import generate_invoice
from app.modules.external.smartme.powermeter_measurement import get_device_by_datetime
from app.modules.external.bitrix24.drive import add_file, get_public_link, get_folder_id, create_folder_path
from app.modules.external.odoo.payment import get_payments_by_contract
from app.models import SherpaInvoice, ContractStatus, OfferV2, Contract, SherpaInvoiceItem, Survey, OfferV2Item
from .annual_statement import generate_annual_statement_pdf
from .calculation import cloud_offer_items_by_pv_offer, calculate_cloud, get_cloud_products


empty_values = [None, "", "0", 0]


def check_contract_data(contract_number, year):
    data = get_contract_data(contract_number)
    statement = get_annual_statement_data(data, year)
    status = ContractStatus.query\
        .filter(ContractStatus.contract_number == contract_number)\
        .filter(ContractStatus.year == year)\
        .first()
    if status is None:
        status = ContractStatus(contract_number=contract_number, year=year)
        db.session.add(status)
    status.has_lightcloud = data["lightcloud"] is not None
    if status.has_lightcloud:
        status.has_begin_date = statement["lightcloud"].get("begin") is not None
        status.has_cloud_number = data["cloud"].get("cloud_number") not in [None, "", 0, "0"]
        status.cloud_number = data["cloud"].get("cloud_number")
        status.has_smartme_number = data["pv_system"]["smartme_number"] not in [None, "", 0, "0", "123"]
        status.has_smartme_number_values = statement["pv_system"].get("total_usage", 0) > 0
    else:
        status.has_begin_date = False
        status.has_cloud_number = False
        status.cloud_number = ""
        status.has_smartme_number = False
        status.has_smartme_number_values = False

    status.has_correct_usage = True
    if statement["pv_system"].get("begin") in [None, 0]:
         status.has_correct_usage = "no usage data"
    else:
        if statement["pv_system"].get("begin") is None or statement["lightcloud"].get("begin") is None:
                status.has_correct_usage = "begin date don't exist"
        else:
            begin1 = parse(statement["pv_system"].get("begin")).strftime("%Y%-m-%d")
            begin2 = parse(statement["lightcloud"].get("begin")).strftime("%Y%-m-%d")
            if begin1 != begin2:
                status.has_correct_usage = f"begin date don't match {begin1} {begin2}"
        if statement["pv_system"].get("end") is None or statement["lightcloud"].get("end") is None:
                status.has_correct_usage = f"end date don't exist {statement['pv_system'].get('end')}"
        else:
            end1 = parse(statement["pv_system"].get("end")).strftime("%Y-%m-%d")
            end2 = parse(statement["lightcloud"].get("end")).strftime("%Y-%m-%d")
            if end1 != end2:
                status.has_correct_usage = f"end date don't match {end1} {end2}"
    status.has_sherpa_values = not statement["pv_system"].get("no_sherpa", False)
    status.has_heatcloud = data["heatcloud"] is not None
    if status.has_heatcloud:
        status.has_smartme_number_heatcloud = data["pv_system"].get("smartme_number_heatcloud") not in [None, "", 0, "0", "123"]
        status.has_smartme_number_heatcloud_values = statement["pv_system"].get("usage_heatcloud", 0) > 0
    else:
        status.has_smartme_number_heatcloud = None
        status.has_smartme_number_heatcloud_values = None
    status.has_consumers = len(data["consumers"]) > 0
    status.has_ecloud = data["ecloud"] is not None
    status.has_emove = data["emove"] is not None
    db.session.commit()


def get_contract_data(contract_number, force_reload=False):
    contract_number = normalize_contract_number(contract_number)
    contract2 = Contract.query.filter(Contract.contract_number == contract_number).first()
    if contract2 is None:
       contract2 = Contract(contract_number=contract_number)
       db.session.add(contract2)
       db.session.commit()
    if force_reload is False and contract2.data is not None:
        return contract2.data
    contract2.data = load_contract_data(contract_number)
    db.session.commit()
    return contract2.data


def load_contract_data(contract_number):
    contract_number = normalize_contract_number(contract_number)
    contract2 = Contract.query.filter(Contract.contract_number == contract_number).first()
    system_config = get_settings(section="external/bitrix24")
    data = {
        "contract_number": contract_number,
        "main_deal": None,
        "cancel_date": None,
        "pv_system": {
            "smartme_number": None,
            "pv_kwp": None,
            "malo_id": None,
            "usages": []
        },
        "data_checks": [],
        "annual_statements": [],
        "configs": [],
        "fakturia": [],
        "payments": [],
    }
    deals = get_deals({
        "SELECT": "full",
        f"filter[{system_config['deal']['fields']['cloud_contract_number']}]": contract_number,
        f"filter[={system_config['deal']['fields']['is_cloud_master_deal']}]": "1",
        "filter[CATEGORY_ID]": 15
    }, force_reload=True)
    if len(deals) > 1:
        return {
            "status": "invalid",
            "errors": [{
                "code": "multiple_masters",
                "message": "Zu viele Aufträge mit 'Ist Cloud Hauptvertrag: Ja'",
                "data": deals
            }]
        }
    if len(deals) < 1:
        deals = get_deals({
            "SELECT": "full",
            f"filter[{system_config['deal']['fields']['cloud_contract_number']}]": contract_number,
            "filter[CATEGORY_ID]": 176
        }, force_reload=True)
        if len(deals) < 1:
            return {
                "status": "invalid",
                "errors": [{
                    "code": "no master",
                    "message": "Kein Auftrag mit 'Ist Cloud Hauptvertrag: Ja' gefunden"
                }]
            }
    data["main_deal"] = deals[0]

    data["contact_id"] = data["main_deal"].get("contact_id")
    data["cancel_date"] = data["main_deal"].get("cancel_date")
    data["pv_system"]["malo_id"] = data["main_deal"].get("malo_id")
    data["pv_system"]["netprovider"] = data["main_deal"].get("netprovider")
    data["pv_system"]["street"] = data["main_deal"].get("cloud_street")
    data["pv_system"]["street_nb"] = data["main_deal"].get("cloud_street_nb")
    data["pv_system"]["city"] = data["main_deal"].get("cloud_city")
    data["pv_system"]["zip"] = data["main_deal"].get("cloud_zip")
    data["pv_system"]["pv_kwp"] = data["main_deal"].get("pv_kwp")
    data["construction_date"] = data["main_deal"].get("construction_date2")
    if data["main_deal"].get("cloud_number") is None:
        data["main_deal"]["cloud_number"] = ""
    cloud_number = data["main_deal"].get("cloud_number").replace(" ", "")
    if data["main_deal"].get("cloud_delivery_begin") not in empty_values and cloud_number not in empty_values:
        data = get_cloud_config(data, cloud_number, data["main_deal"].get("cloud_delivery_begin"), data["main_deal"].get("cloud_delivery_begin_1"), first_delivery=True)
    if data["main_deal"].get("cloud_delivery_begin_1") not in empty_values and data["main_deal"].get("cloud_number_1") not in empty_values:
        data = get_cloud_config(data, data["main_deal"].get("cloud_number_1"), data["main_deal"].get("cloud_delivery_begin_1"), data["main_deal"].get("cloud_delivery_begin_2"))
    if data["main_deal"].get("cloud_delivery_begin_2") not in empty_values and data["main_deal"].get("cloud_number_2") not in empty_values:
        data = get_cloud_config(data, data["main_deal"].get("cloud_number_2"), data["main_deal"].get("cloud_delivery_begin_2"), data["main_deal"].get("cloud_delivery_begin_3"))
    if data["main_deal"].get("cloud_delivery_begin_3") not in empty_values and data["main_deal"].get("cloud_number_3") not in empty_values:
        data = get_cloud_config(data, data["main_deal"].get("cloud_number_3"), data["main_deal"].get("cloud_delivery_begin_3"))

    min_delivery_begin = None
    for config in data["configs"]:
        if config["delivery_begin"] not in [None, ""] and (min_delivery_begin is None or min_delivery_begin > parse(config["delivery_begin"])):
            min_delivery_begin = parse(config["delivery_begin"])
        if config["earliest_delivery_begin"] not in [None, ""] and (min_delivery_begin is None or min_delivery_begin > parse(config["earliest_delivery_begin"])):
            min_delivery_begin = parse(config["earliest_delivery_begin"])
    if min_delivery_begin is not None:
        for year in range(min_delivery_begin.year, datetime.datetime.now().year + 1):
            annual_statement = {
                "year": year,
                "status": [],
                "deal": None,
                "data": None,
                "manuell_data": {
                    "assumed_autocracy_lightcloud": 50,
                    "assumed_autocracy_heatcloud": 28
                }
            }
            contract_status = ContractStatus.query.filter(ContractStatus.year == str(year)).filter(ContractStatus.contract_number == contract_number).first()
            if contract_status is not None:
                if contract_status.to_pay is not None:
                    annual_statement["price_net"] = float(contract_status.to_pay) / 1.19
                    annual_statement["price"] = float(contract_status.to_pay)
                if contract_status.pdf_file_id is not None and contract_status.pdf_file_id > 0:
                    annual_statement["pdf_link"] = get_public_link(contract_status.pdf_file_id)
                if contract_status.manuell_data is not None:
                    annual_statement["manuell_data"] = contract_status.manuell_data
                    if annual_statement["manuell_data"].get("assumed_autocracy_lightcloud") in [None, "", 0, "0"]:
                        annual_statement["manuell_data"]["assumed_autocracy_lightcloud"] = 50
                    if annual_statement["manuell_data"].get("assumed_autocracy_heatcloud") in [None, "", 0, "0"]:
                        annual_statement["manuell_data"]["assumed_autocracy_heatcloud"] = 28
                annual_statement["data"] = contract_status.data

            deals = get_deals({
                "SELECT": "full",
                f"filter[{system_config['deal']['fields']['cloud_contract_number']}]": contract_number,
                "filter[CATEGORY_ID]": 126
            }, force_reload=True)
            if len(deals) > 0:
                annual_statement["deal"] = {
                    "id": deals[0]["id"],
                    "stage_id": deals[0]["stage_id"],
                    "title": deals[0]["title"]
                }
                annual_statement["status"].append("has_status")
                if deals[0]["stage_id"] == "C126:NEW":
                    annual_statement["status"].append("is_generated")
                    annual_statement["deal"]["status"] = "Neu"
                if deals[0]["stage_id"] == "C126:UC_XM96DH":
                    annual_statement["status"].append("report_2022")
                    annual_statement["deal"]["status"] = "Abrechnung 2022"
                if deals[0]["stage_id"] == "C126:UC_883FVL":
                    annual_statement["status"].append("old_contract")
                    annual_statement["deal"]["status"] = "Altvertrag manuelle bearbeitung"
                if deals[0]["stage_id"] == "C126:UC_FVSJ2M":
                    annual_statement["status"].append("special_custumer")
                    annual_statement["deal"]["status"] = "Spezialkunde"
                if deals[0]["stage_id"] == "C126:UC_CQNYI7":
                    annual_statement["status"].append("orgamaxx_customer")
                    annual_statement["deal"]["status"] = "Orgamaxx Kunde"
                if deals[0]["stage_id"] == "C126:UC_FT4TL0":
                    annual_statement["status"].append("bsh_data")
                    annual_statement["deal"]["status"] = "Senec Werte-Abfrage BSH"
                if deals[0]["stage_id"] == "C126:UC_DZZRWI":
                    annual_statement["status"].append("bsh_data")
                    annual_statement["deal"]["status"] = "Senec Wert gemeldet"
                if deals[0]["stage_id"] == "C126:UC_XPBTZ9":
                    annual_statement["status"].append("request_consumer_data")
                    annual_statement["deal"]["status"] = "Consumer Daten erfragen"
                if deals[0]["stage_id"] == "C126:PREPARATION":
                    annual_statement["status"].append("waiting for data")
                    annual_statement["deal"]["status"] = "Daten von Kunden anfragen"
                if deals[0]["stage_id"] in ["C126:UC_RZ52LY"]:
                    annual_statement["deal"]["status"] = "Abrechnung an Kunde senden"
                if deals[0]["stage_id"] in ["C126:UC_T3E3U2"]:
                    annual_statement["deal"]["status"] = "BSH Prüfung"
                if deals[0]["stage_id"] in ["C126:PREPAYMENT_INVOICE"]:
                    annual_statement["status"].append("manuell_check")
                    annual_statement["deal"]["status"] = "E360 Prüfung"
                if deals[0]["stage_id"] == "C126:EXECUTING":
                    annual_statement["deal"]["status"] = "Orgamaxx Rechnung erstellen"
                if deals[0]["stage_id"] == "C126:UC_L0M7DR":
                    annual_statement["status"].append("wartet auf Zahlung")
                    annual_statement["deal"]["status"] = "Fakturia Zahlung erzeugen"
                if deals[0]["stage_id"] == "C126:UC_RBVLQV":
                    annual_statement["status"].append("Korrektur nötog")
                    annual_statement["deal"]["status"] = "Abrechnungskorrektur erzeugen"
                if deals[0]["stage_id"] == "C126:WON":
                    annual_statement["status"].append("done")
                    annual_statement["deal"]["status"] = "Abgeschossen"

            data["annual_statements"].append(annual_statement)

    data["fakturia"] = get_contract(contract_number)
    data["invoices_credit_notes"] = get_payments(contract_number)
    if data["fakturia"] is not None and "accountNumber" in data["fakturia"]:
        data["payments"] = get_payments2(data["fakturia"]["accountNumber"])

    return data

    if deals is not None:
        if len(deals) == 1:
            if deals[0].get("is_cloud_master_deal") not in [True, "1", 1]:
                update_deal(deals[0].get("id"), {"is_cloud_master_deal": "1"})
                deals[0]["is_cloud_master_deal"] = "1"
        else:
            has_master = False
            for deal in deals:
                if deal.get("is_cloud_master_deal") in [True, "1", 1]:
                    has_master = True
            if has_master is False:
                for deal in deals:
                    if deal.get("is_cloud_consumer") not in [True, "1", 1] and deal.get("is_cloud_ecloud") not in [True, "1", 1] and deal.get("is_cloud_heatcloud") not in [True, "1", 1]:
                        if deal.get("category_id") in [15, "15"]:
                            print(deal.get("id"), deal.get("category_id"))
                            update_deal(deal.get("id"), {"is_cloud_master_deal": "1"})
                            deal["is_cloud_master_deal"] = "1"

        data["deals"] = deals
        for deal in deals:
            if deal.get("is_cloud_master_deal") in [True, "1", 1]:
                data["contact_id"] = deal.get("contact_id")
                if data["pv_system"].get("smartme_number") in [None, "", 0, "0", "123"]:
                    data["pv_system"]["smartme_number"] = deal.get("smartme_number")
                if data["pv_system"].get("smartme_number_heatcloud") in [None, "", 0, "0", "123"]:
                    data["pv_system"]["smartme_number_heatcloud"] = deal.get("smartme_number_heatcloud")
                data["pv_system"]["pv_kwp"] = deal.get("pv_kwp")
                data["pv_system"]["malo_id"] = deal.get("malo_id")
                data["pv_system"]["power_meter_number"] = deal.get("power_meter_number")
                data["pv_system"]["street"] = deal.get("cloud_street")
                data["pv_system"]["street_nb"] = deal.get("cloud_street_nb")
                data["pv_system"]["city"] = deal.get("cloud_city")
                data["pv_system"]["zip"] = deal.get("cloud_zip")
                data["pv_system"]["netprovider"] = deal.get("netprovider")
                data["cloud"]["cloud_monthly_price"] = float(deal.get("cloud_monthly_price").replace(".", "").replace(",", "."))
                data["cloud"]["extra_price_per_kwh"] = deal.get("extra_price_per_kwh")
                data["cloud"]["cashback_per_kwh"] = deal.get("cashback_per_kwh")
                data["cloud"]["cloud_number"] = deal.get("cloud_number")
                offer = OfferV2.query.filter(OfferV2.number == data["cloud"]["cloud_number"]).first()
                if offer is not None:
                    data["cloud"]["pdf_link"] = offer.pdf.public_link
                if data["cloud"]["cloud_number"] not in [None, "", 0, "0"]:
                    offer = OfferV2.query.filter(OfferV2.number == data["cloud"]["cloud_number"]).first()
                    if offer is not None:
                        data["cloud"]["cloud_monthly_price"] = offer.calculated["cloud_price_incl_refund"]
                        data["cloud"]["calculated"] = offer.calculated
                        data["cloud"]["data"] = offer.data
                data["lightcloud"] = {
                    "status": get_item_status(deal),
                    "usage": deal.get("lightcloud_usage"),
                    "delivery_begin": deal.get("cloud_delivery_begin"),
                    "cancelation_date": deal.get("cancelation_date"),
                    "cancelation_due_date": deal.get("cancelation_due_date")
                }
                if deal.get("cloud_delivery_begin") not in ["", None] and contract2 is not None and contract2.begin != parse(deal.get("cloud_delivery_begin")):
                    contract2.begin = parse(deal.get("cloud_delivery_begin"))
                    db.session.commit()

                if deal.get("has_emove_package") not in ["none", None, "0", 0, "", False, "false", "Nein"]:
                    print("lkncy", deal.get("has_emove_package"))
                    data["emove"] = {
                        "status": get_item_status(deal),
                        "packet": "eMove",
                        "usage_inhouse": deal.get("emove_usage_inhouse"),
                        "usage_outside": deal.get("emove_usage_outside"),
                        "delivery_begin": deal.get("cloud_delivery_begin"),
                        "cancelation_date": deal.get("cancelation_date"),
                        "cancelation_due_date": deal.get("cancelation_due_date")
                    }
                    if data["cloud"].get("data") is not None:
                        data["emove"]["packet"] = data["cloud"]["data"].get("emove_tarif")
            if deal.get("is_cloud_heatcloud") in [True, "1", 1]:
                if data["pv_system"].get("smartme_number_heatcloud") in [None, "", 0, "0", "123"]:
                    data["pv_system"]["smartme_number_heatcloud"] = deal.get("smartme_number_heatcloud")
                data["heatcloud"] = {
                    "status": get_item_status(deal),
                    "power_meter_number": deal.get("heatcloud_power_meter_number"),
                    "usage": deal.get("heatcloud_usage"),
                    "delivery_begin": deal.get("cloud_delivery_begin"),
                    "cancelation_date": deal.get("cancelation_date"),
                    "cancelation_due_date": deal.get("cancelation_due_date")
                }
            if deal.get("is_cloud_ecloud") in [True, "1", 1]:
                data["ecloud"] = {
                    "status": get_item_status(deal),
                    "usage": deal.get("ecloud_usage"),
                    "delivery_begin": deal.get("cloud_delivery_begin"),
                    "cancelation_date": deal.get("cancelation_date"),
                    "cancelation_due_date": deal.get("cancelation_due_date")
                }
            if deal.get("is_consumer") in [True, "1", 1]:
                data["consumers"].append({
                    "status": get_item_status(deal),
                    "usage": deal.get("lightcloud_usage"),
                    "power_meter_number": deal.get("power_meter_number"),
                    "street": deal.get("cloud_street"),
                    "street_nb": deal.get("cloud_street_nb"),
                    "city": deal.get("cloud_city"),
                    "zip": deal.get("cloud_zip"),
                    "netprovider": deal.get("netprovider"),
                    "delivery_begin": deal.get("cloud_delivery_begin"),
                    "cancelation_date": deal.get("cancelation_date"),
                    "cancelation_due_date": deal.get("cancelation_due_date")
                })
    if "contact_id" in data:
        data["contact"] = get_contact(data["contact_id"])
    if data["pv_system"].get("smartme_number") not in [None, "", "0", 0] and data["lightcloud"].get("delivery_begin") not in [None, "", "0", 0]:
        delivery_begin = parse(data["lightcloud"].get("delivery_begin"))
        start_year = delivery_begin.year
        end_year = datetime.datetime.now().year
        for year in range(start_year, end_year + 1):
            if delivery_begin.year == year:
                beginning_of_year = get_device_by_datetime(data["pv_system"].get("smartme_number"), data["lightcloud"].get("delivery_begin"))
            else:
                beginning_of_year = get_device_by_datetime(data["pv_system"].get("smartme_number"), f"{year}-01-01 00:00:00")
            if beginning_of_year is None:
                continue
            end_of_year = get_device_by_datetime(data["pv_system"].get("smartme_number"), f"{year}-12-31 23:59:59")
            values = {
                "year": year,
                "number": data["pv_system"].get("smartme_number"),
                "start_date": beginning_of_year.get("Date"),
                "start_value": abs(beginning_of_year.get("CounterReading", 0)),
                "end_date": end_of_year.get("Date"),
                "end_value": abs(end_of_year.get("CounterReading", 0))
            }
            values["usage"] = values["end_value"] - values["start_value"]
            data["pv_system"]["usages"].append(values)
    if data["pv_system"].get("smartme_number_heatcloud") not in [None, "", "0", 0]:
        data["pv_system"]["heatcloud_usages"] = []
        if data["heatcloud"].get("delivery_begin") not in [None, ""]:
            delivery_begin = parse(data["heatcloud"].get("delivery_begin"))
            start_year = delivery_begin.year
            end_year = datetime.datetime.now().year
            for year in range(start_year, end_year + 1):
                if delivery_begin.year == year:
                    beginning_of_year = get_device_by_datetime(data["pv_system"].get("smartme_number_heatcloud"), data["heatcloud"].get("delivery_begin"))
                else:
                    beginning_of_year = get_device_by_datetime(data["pv_system"].get("smartme_number_heatcloud"), f"{year}-01-01 00:00:00")
                if beginning_of_year is None:
                    continue
                end_of_year = get_device_by_datetime(data["pv_system"].get("smartme_number_heatcloud"), f"{year}-12-31 23:59:59")
                values = {
                    "year": year,
                    "number": data["pv_system"].get("smartme_number_heatcloud"),
                    "start_date": beginning_of_year.get("Date"),
                    "start_value": abs(beginning_of_year.get("CounterReading", 0)),
                    "end_date": end_of_year.get("Date"),
                    "end_value": abs(end_of_year.get("CounterReading", 0))
                }
                values["usage"] = values["end_value"] - values["start_value"]
                data["pv_system"]["heatcloud_usages"].append(values)
    data["payments"] = get_payments(contract_number)
    contract2.data = data
    db.session.commit()
    return data


def get_cloud_config(data, cloud_number, delivery_begin, delivery_end, first_delivery=False):
    settings = get_settings(section="external/bitrix24")
    config = {
        "cloud_number": cloud_number,
        "earliest_delivery_begin": delivery_begin,
        "delivery_begin": delivery_begin,
        "delivery_end": None,
        "consumers": [],
        "errors": []
    }
    if delivery_end not in empty_values:
        config["delivery_end"] = str(normalize_date(delivery_end) - datetime.timedelta(days=1))
    else:
        if data.get("cancel_date") not in empty_values:
            config["delivery_end"] = data.get("cancel_date")
    config["measuring_concept"] = data["main_deal"].get("measuring_concept")
    legacy_cloud = False
    offer_v2 = OfferV2.query.filter(OfferV2.number == cloud_number).first()
    print('why?', offer_v2)
    if offer_v2 is None:
        survey = None
        try:
            offer_v2 = OfferV2.query.filter(OfferV2.id == int(cloud_number.replace("C-", ""))).first()
            survey = Survey.query.filter(Survey.id == offer_v2.survey_id).first()
        except Exception as e:
            pass
        if survey is None:
            offer_v2 = None
            config["errors"].append({
                "code": "config not found",
                "message": "Angebotsnummer konnte nicht gefunden werden."
            })
        else:
            legacy_cloud = True
            legacy_data = cloud_offer_items_by_pv_offer(offer_v2, True)
            del legacy_data["datetime"]
            offer_v2.data = legacy_data["data"]
            offer_v2.calculated = legacy_data["calculated"]
            offer_v2.calculated["cloud_price"] = legacy_data["total"]
            offer_v2.calculated["power_usage"] = round(offer_v2.calculated["power_usage"] / 10) * 10
            offer_v2.calculated["lightcloud_extra_price_per_kwh"] = 0.3379
            offer_v2.calculated["heatcloud_extra_price_per_kwh"] = 0.3379
            offer_v2.calculated["consumercloud_extra_price_per_kwh"] = 0.3379
            offer_v2.calculated["ecloud_extra_price_per_kwh"] = 0.1199

    if offer_v2 is not None:
        if offer_v2.data.get("old_cloud_number") not in [None, ""]:
            config["old_cloud_number"] = offer_v2.data.get("old_cloud_number")
        data["pv_system"]["pv_kwp"] = offer_v2.calculated.get("pv_kwp")
        data["pv_system"]["storage_size"] = offer_v2.calculated.get("storage_size")
        if legacy_cloud:
            config["pdf_link"] = offer_v2.cloud_pdf.public_link
        else:
            if offer_v2.pdf is not None:
                config["pdf_link"] = offer_v2.pdf.public_link

        config["cloud_price"] = offer_v2.calculated.get("cloud_price")
        config["cloud_price_incl_refund"] = offer_v2.calculated.get("cloud_price_incl_refund")
        config["cloud_price_incl_refund_net"] = offer_v2.calculated.get("cloud_price_incl_refund") / 1.19
        config["cloud_price_extra"] = offer_v2.calculated.get("cloud_price_extra"),
        if offer_v2.datetime >= datetime.datetime(2021,12,16,0,0,0):
            config["cashback_price_per_kwh"] = 0.08
        else:
            config["cashback_price_per_kwh"] = 0.10
        config["ecloud_cashback_price_per_kwh"] = 0.04
        if offer_v2.calculated.get("cashback_price_per_kwh") is not None:
            config["cashback_price_per_kwh"] = offer_v2.calculated.get("cashback_price_per_kwh")
        if offer_v2.calculated.get("ecloud_cashback_price_per_kwh") is not None:
            config["ecloud_cashback_price_per_kwh"] = offer_v2.calculated.get("ecloud_cashback_price_per_kwh")
        config["pv_kwp"] = offer_v2.data.get("pv_kwp")
        config["pv_kwp_overwrite"] = offer_v2.data.get("pv_kwp_overwrite")
        if offer_v2.calculated.get("min_kwp_light") > 0:
            config["lightcloud"] = {
                "label": "Lichtcloud",
                "usage": offer_v2.calculated.get("power_usage"),
                "min_kwp": offer_v2.calculated.get("min_kwp_light"),
                "min_kwp_overwrite": offer_v2.data.get("lightcloud_min_kwp_overwrite"),
                "extra_price_per_kwh": offer_v2.calculated.get("lightcloud_extra_price_per_kwh"),
                "extra_price_per_kwh_overwrite": offer_v2.data.get("lightcloud_extra_price_per_kwh_overwrite"),
                "cloud_price": offer_v2.calculated.get(f"cloud_price_light"),
                "cloud_price_overwrite": offer_v2.data.get("lightcloud_cloud_price_overwrite"),
                "cloud_price_incl_refund": offer_v2.calculated.get("cloud_price_light_incl_refund"),
                "smartme_number": string_stripper(data["main_deal"].get("smartme_number")),
                "power_meter_number": string_stripper(data["main_deal"].get("delivery_counter_number")),
                "additional_power_meter_numbers": [],
                "additional_smartme_numbers": [],
                "delivery_begin": data["main_deal"].get("cloud_delivery_begin"),
                "deal": {
                    "id": data["main_deal"].get("id"),
                    "title": data["main_deal"].get("title")
                }
            }
            if config["lightcloud"]["smartme_number"] not in empty_values:
                config["lightcloud"]["smartme_number"] = string_stripper(config["lightcloud"]["smartme_number"])
            if config["lightcloud"]["power_meter_number"] not in empty_values:
                config["lightcloud"]["power_meter_number"] = string_stripper(config["lightcloud"]["power_meter_number"])
            if data["main_deal"].get("delivery_counter_number2") not in empty_values:
                config["lightcloud"]["additional_power_meter_numbers"].append(data["main_deal"].get("delivery_counter_number2"))
            if data["main_deal"].get("delivery_counter_number3") not in empty_values:
                config["lightcloud"]["additional_power_meter_numbers"].append(data["main_deal"].get("delivery_counter_number3"))
            if data["main_deal"].get("old_power_meter_numbers") not in empty_values:
                numbers = data["main_deal"].get("old_power_meter_numbers").split("\n")
                for number in numbers:
                    number = string_stripper(number)
                    if number != "" and number not in config["lightcloud"]["additional_power_meter_numbers"]:
                        config["lightcloud"]["additional_power_meter_numbers"].append(number)
            if data["main_deal"].get("old_smartme_numbers") not in empty_values:
                if isinstance(data["main_deal"].get("old_smartme_numbers"), list):
                    numbers = data["main_deal"].get("old_smartme_numbers")
                else:
                    numbers = data["main_deal"].get("old_smartme_numbers").split("\n")
                for number in numbers:
                    number = string_stripper(number)
                    if number != "" and number not in config["lightcloud"]["additional_smartme_numbers"]:
                        config["lightcloud"]["additional_smartme_numbers"].append(number)

        if offer_v2.calculated.get("min_kwp_emove") > 0:
            emove_usage_inhouse = data["main_deal"].get("emove_usage_inhouse")
            emove_usage_outside = data["main_deal"].get("emove_usage_outside")
            if emove_usage_inhouse is not None:
                emove_usage_inhouse = float(emove_usage_inhouse)
            if emove_usage_outside is not None:
                emove_usage_outside = float(emove_usage_outside)
            config["emove"] = {
                "label": "eMove",
                "tarif": offer_v2.data.get("emove_tarif"),
                "min_kwp": offer_v2.calculated.get("min_kwp_emove"),
                "cloud_price": offer_v2.calculated.get(f"cloud_price_emove"),
                "cloud_price_incl_refund": offer_v2.calculated.get("cloud_price_emove_incl_refund"),
                "extra_price_per_kwh": offer_v2.calculated.get("lightcloud_extra_price_per_kwh"),
                "usage": emove_usage_inhouse,
                "usage_outside": emove_usage_outside,
                "delivery_begin": data["main_deal"].get("cloud_delivery_begin"),
                "deal": {
                    "id": data["main_deal"].get("id"),
                    "title": data["main_deal"].get("title")
                }
            }
        if offer_v2.calculated.get("min_kwp_heatcloud") > 0:
            config["heatcloud"] = {
                "label": "Wärmecloud",
                "usage": offer_v2.calculated.get("heater_usage"),
                "min_kwp": offer_v2.calculated.get("min_kwp_heatcloud"),
                "cloud_price": offer_v2.calculated.get(f"cloud_price_heatcloud"),
                "cloud_price_incl_refund": offer_v2.calculated.get("cloud_price_heatcloud_incl_refund"),
                "extra_price_per_kwh": offer_v2.calculated.get("heatcloud_extra_price_per_kwh"),
                "additional_power_meter_numbers": [],
                "additional_smartme_numbers": [],
                "deal": None
            }
            deals = get_deals({
                "SELECT": "full",
                f"filter[{settings['deal']['fields']['cloud_contract_number']}]": data["contract_number"],
                f"filter[={settings['deal']['fields']['is_cloud_heatcloud']}]": "1",
                "filter[CATEGORY_ID]": 15
            }, force_reload=True)
            if len(deals) != 1:
                config["errors"].append({
                    "code": "deal_not_found",
                    "message": "Wärmecloud Auftrag nicht gefunden"
                })
            else:
                config["heatcloud"]["smartme_number"] = string_stripper(deals[0].get("smartme_number_heatcloud"))
                config["heatcloud"]["power_meter_number"] = string_stripper(deals[0].get("heatcloud_power_meter_number"))
                config["heatcloud"]["delivery_begin"] = deals[0].get("cloud_delivery_begin")
                if config["heatcloud"]["delivery_begin"] not in ["", None]:
                    if parse(config["earliest_delivery_begin"]) > parse(config["heatcloud"]["delivery_begin"]):
                        config["earliest_delivery_begin"] =  config["heatcloud"]["delivery_begin"]
                config["heatcloud"]["deal"] = {
                    "id": deals[0].get("id"),
                    "title": deals[0].get("title")
                }
                print("heat", deals[0].get("id"))
                if config["heatcloud"]["power_meter_number"] not in empty_values:
                    config["heatcloud"]["power_meter_number"] = string_stripper(config["heatcloud"]["power_meter_number"])
                if deals[0].get("old_power_meter_numbers") not in empty_values:
                    numbers =  deals[0].get("old_power_meter_numbers").split("\n")
                    for number in numbers:
                        number = string_stripper(number)
                        if number != "" and number not in config["heatcloud"]["additional_power_meter_numbers"]:
                            config["heatcloud"]["additional_power_meter_numbers"].append(number)
                if deals[0].get("old_smartme_numbers") not in empty_values:
                    if isinstance(deals[0].get("old_smartme_numbers"), list):
                        numbers = deals[0].get("old_smartme_numbers")
                    else:
                        numbers = deals[0].get("old_smartme_numbers").split("\n")
                    for number in numbers:
                        number = string_stripper(number)
                        if number != "" and number not in config["heatcloud"]["additional_smartme_numbers"]:
                            config["heatcloud"]["additional_smartme_numbers"].append(number)
        if offer_v2.calculated.get("min_kwp_ecloud") > 0:
            config["ecloud"] = {
                "label": "eCloud",
                "usage": offer_v2.calculated.get("ecloud_usage"),
                "min_kwp": offer_v2.calculated.get("min_kwp_ecloud"),
                "power_meter_number": None,
                "additional_power_meter_numbers": [],
                "cloud_price": offer_v2.calculated.get(f"cloud_price_ecloud"),
                "cloud_price_incl_refund": offer_v2.calculated.get("cloud_price_ecloud_incl_refund"),
                "extra_price_per_kwh": offer_v2.calculated.get("ecloud_extra_price_per_kwh"),
                "deal": None
            }
            deals = get_deals({
                "SELECT": "full",
                f"filter[{settings['deal']['fields']['cloud_contract_number']}]": data["contract_number"],
                f"filter[={settings['deal']['fields']['is_cloud_ecloud']}]": "1",
                "filter[CATEGORY_ID]": 15
            }, force_reload=True)
            if len(deals) != 1:
                config["errors"].append({
                    "code": "deal_not_found",
                    "message": "eCloud Auftrag nicht gefunden"
                })
            else:
                config["ecloud"]["smartme_number"] = None
                config["ecloud"]["power_meter_number"] = string_stripper(deals[0].get("counter_ecloud"))
                config["ecloud"]["delivery_begin"] = deals[0].get("cloud_delivery_begin")
                if config["ecloud"]["delivery_begin"] not in ["", None]:
                    if parse(config["earliest_delivery_begin"]) > parse(config["ecloud"]["delivery_begin"]):
                        config["earliest_delivery_begin"] =  config["ecloud"]["delivery_begin"]
                config["ecloud"]["deal"] = {
                    "id": deals[0].get("id"),
                    "title": deals[0].get("title")
                }
                if config["ecloud"]["power_meter_number"] not in empty_values:
                    config["ecloud"]["power_meter_number"] = string_stripper(config["ecloud"]["power_meter_number"])
                if deals[0].get("old_power_meter_numbers") not in empty_values:
                    numbers =  deals[0].get("old_power_meter_numbers").split("\n")
                    for number in numbers:
                        number = string_stripper(number)
                        if number != "" and number not in config["ecloud"]["additional_power_meter_numbers"]:
                            config["ecloud"]["additional_power_meter_numbers"].append(number)
                if data["main_deal"].get("old_power_meter_numbers_ecloud") not in empty_values:
                    numbers = data["main_deal"].get("old_power_meter_numbers_ecloud").split("\n")
                    for number in numbers:
                        number = string_stripper(number)
                        if number != "" and number not in config["ecloud"]["additional_power_meter_numbers"]:
                            config["ecloud"]["additional_power_meter_numbers"].append(number)
                if deals[0].get("old_power_meter_numbers_ecloud") not in empty_values:
                    numbers = deals[0].get("old_power_meter_numbers_ecloud").split("\n")
                    for number in numbers:
                        number = string_stripper(number)
                        if number != "" and number not in config["ecloud"]["additional_power_meter_numbers"]:
                            config["ecloud"]["additional_power_meter_numbers"].append(number)
        if offer_v2.calculated.get("min_kwp_consumer") > 0:
            config["consumer_min_kwp"] = offer_v2.data.get("consumer_min_kwp")
            config["consumer_min_kwp_overwrite"] = offer_v2.data.get("consumer_min_kwp_overwrite")
            config["consumer_cloud_price_overwrite"] = offer_v2.data.get("consumer_cloud_price_overwrite")
            config["consumer_extra_price_per_kwh_overwrite"] = offer_v2.data.get("consumer_extra_price_per_kwh_overwrite")
            for index, consumer in enumerate(offer_v2.data.get("consumers")):
                config["consumers"].append({
                    "label": f"Consumer {index + 1}",
                    "usage": int(consumer.get("usage")),
                    "address": consumer.get("address"),
                    "power_meter_number": None,
                    "additional_power_meter_numbers": [],
                    "cloud_price": offer_v2.calculated.get(f"cloud_price_consumer") / len(offer_v2.data.get("consumers")),
                    "cloud_price_incl_refund": offer_v2.calculated.get("cloud_price_consumer_incl_refund") / len(offer_v2.data.get("consumers")),
                    "extra_price_per_kwh": offer_v2.calculated.get("consumercloud_extra_price_per_kwh"),
                    "deal": None
                })
            deals = get_deals({
                "SELECT": "full",
                f"filter[{settings['deal']['fields']['cloud_contract_number']}]": data["contract_number"],
                f"filter[={settings['deal']['fields']['is_cloud_consumer']}]": "1",
                "filter[CATEGORY_ID]": 15
            }, force_reload=True)
            for index, consumer in enumerate(config["consumers"]):
                existing_deal = next((i for i in deals if str(i["delivery_usage"]) == str(consumer["usage"]) and i.get("is_used") is not True), None)
                if existing_deal is None:
                    config["errors"].append({
                        "code": "deal_not_found",
                        "message": f"Consumer {index + 1} Auftrag nicht gefunden"
                    })
                else:
                    consumer["power_meter_number"] = string_stripper(existing_deal.get("delivery_counter_number"))
                    consumer["delivery_begin"] = existing_deal.get("cloud_delivery_begin")
                    if consumer["delivery_begin"] not in ["", None]:
                        if parse(config["earliest_delivery_begin"]) > parse(consumer["delivery_begin"]):
                            config["earliest_delivery_begin"] = consumer["delivery_begin"]
                    if existing_deal.get("old_power_meter_numbers") not in empty_values:
                        numbers =  existing_deal.get("old_power_meter_numbers").split("\n")
                        for number in numbers:
                            number = string_stripper(number)
                            if number != "" and number not in consumer["additional_power_meter_numbers"]:
                                consumer["additional_power_meter_numbers"].append(number)
                    consumer["deal"] = {
                        "id": existing_deal.get("id"),
                        "title": existing_deal.get("title")
                    }
                    existing_deal["is_used"] = True
            config["consumer_data"] = {
                "cloud_price": offer_v2.calculated.get(f"cloud_price_consumer"),
                "cloud_price_incl_refund": offer_v2.calculated.get("cloud_price_consumer_incl_refund"),
                "extra_price_per_kwh": offer_v2.calculated.get("consumercloud_extra_price_per_kwh"),
            }
    if first_delivery and normalize_date(config["earliest_delivery_begin"]) < normalize_date(config["delivery_begin"]):
        config["delivery_begin"] = config["earliest_delivery_begin"]
    data["configs"].append(config)
    return data


def get_annual_statement_data(data, year, manuell_data):
    year = int(year)
    if manuell_data is None:
        manuell_data = {
            "corrected_datediff": True
        }
    statement = {
        "year": year,
        "contact": get_contact(data.get("contact_id")),
        "measuring_concept": data.get("measuring_concept"),
        "construction_date": data.get("construction_date"),
        "counters": [],
        "configs": [],
        "errors": [],
        "warnings": [],
        "pv_system": data["pv_system"],
        "total_usage": 0,
        "taxrate": 19,
        "total_extra_usage": 0,
        "total_extra_price": 0,
        "total_extra_price_net": 0,
        "total_cloud_price": 0,
        "total_cloud_price_net": 0,
        "total_cloud_price_incl_refund": 0,
        "total_cloud_price_incl_refund_net": 0,
        "available_values": [],
        "extra_price_per_kwh": 0.27
    }
    counter_numbers = []
    sherpa_counters = []
    sherpaInvoices = SherpaInvoice.query\
        .filter(SherpaInvoice.identnummer == data.get("contract_number"))\
        .filter(SherpaInvoice.abrechnungszeitraum_von >= f"{year}-01-01") \
        .filter(SherpaInvoice.abrechnungszeitraum_von <= f"{year}-12-31") \
        .order_by(SherpaInvoice.id.asc()) \
        .all()
    for sherpaInvoice in sherpaInvoices:
        sherpa_items = SherpaInvoiceItem.query.filter(SherpaInvoiceItem.sherpa_invoice_id == sherpaInvoice.id).all()
        for item in sherpa_items:
            existing_counter = next((i for i in sherpa_counters if i["number"] == item.zahlernummer and i["start_date"] == str(item.datum_stand_alt) and i["end_date"] == str(item.datum_stand_neu)), None)
            if existing_counter is not None:
                if existing_counter["sherpa_invoice_id"] == item.sherpa_invoice_id:
                    existing_counter["start_value"] = existing_counter["start_value"] + item.stand_alt
                    existing_counter["end_value"] = existing_counter["end_value"] + item.stand_neu
                    existing_counter["usage"] = existing_counter["usage"] + item.verbrauch
                else:
                    existing_counter["sherpa_invoice_id"] = item.sherpa_invoice_id
                    existing_counter["start_value"] = item.stand_alt
                    existing_counter["end_value"] = item.stand_neu
                    existing_counter["usage"] = item.verbrauch
            else:
                sherpa_counters.append({
                    "number": item.zahlernummer,
                    "sherpa_invoice_id": item.sherpa_invoice_id,
                    "type": "Zähler",
                    "start_date": str(item.datum_stand_alt),
                    "start_value": item.stand_alt,
                    "end_date": str(item.datum_stand_neu),
                    "end_value": item.stand_neu,
                    "usage": item.verbrauch
                })
    for item in sherpa_counters:
        statement["available_values"].append({
            "number": item.get("number"),
            "date": normalize_date(item.get("start_date")),
            "value": item.get("start_value"),
            "origin": "Netzbetreiber",
        })
        statement["available_values"].append({
            "number": item.get("number"),
            "date": normalize_date(item.get("end_date")),
            "value": item.get("end_value"),
            "origin": "Netzbetreiber",
        })

    for config in data["configs"]:
        statement_config = json.loads(json.dumps(config))
        customer_products = []
        for index, consumer in enumerate(statement_config["consumers"]):
            customer_products.append(f"consumer{index}")
            statement_config[f"consumer{index}"] = consumer
        statement_config["customer_products"] = customer_products

        if manuell_data.get("cashback_price_per_kwh") not in [None, ""]:
            statement_config["cashback_price_per_kwh"] = float(manuell_data.get("cashback_price_per_kwh")) / 100
        if manuell_data.get("ecloud_cashback_price_per_kwh") not in [None, ""]:
            statement_config["ecloud_cashback_price_per_kwh"] = float(manuell_data.get("ecloud_cashback_price_per_kwh")) / 100
        statement_config["taxrate"] = statement["taxrate"]
        statement_config["total_usage"] = 0
        statement_config["total_extra_usage"] = 0
        statement_config["total_extra_price"] = 0
        statement_config["total_extra_price_net"] = 0
        statement_config["total_cloud_price"] = 0
        statement_config["total_cloud_price_net"] = 0
        statement_config["total_cloud_price_incl_refund"] = 0
        statement_config["total_cloud_price_incl_refund_net"] = 0
        delivery_end = str(year) + "-12-31"
        if config.get("delivery_end") is not None and parse(config.get("delivery_end")).year == year:
            delivery_end = str(config.get("delivery_end"))
        delivery_begin = str(year) + "-01-01"
        if parse(config.get("delivery_begin")).year == year:
            delivery_begin = str(config.get("delivery_begin"))
        if parse(config.get("delivery_begin")).year > year:
            continue
        if statement.get("delivery_begin") is None:
            statement["delivery_begin"] = delivery_begin
        if statement.get("delivery_end") is None or normalize_date(statement.get("delivery_end")) < normalize_date(delivery_end):
            statement["delivery_end"] = delivery_end
        if parse(delivery_begin).year <= year and parse(delivery_end).year >= year:
            for product in ["heatcloud", "lightcloud", "ecloud"] + customer_products:
                if statement_config.get(product) is None:
                    continue
                if statement_config[product].get("delivery_begin") in [None, "", 0, "0"]:
                    del statement_config[product]
                    continue
                if parse(statement_config[product].get("delivery_begin")).year > year:
                    del statement_config[product]
                    continue
                if config.get("delivery_end") not in [None, "", 0] and normalize_date(statement_config[product].get("delivery_begin")) >= normalize_date(config.get("delivery_end")):
                    del statement_config[product]
                    continue
                statement_config[product]["taxrate"] = statement_config["taxrate"]
                if product == "ecloud" and year == 2022:
                    statement_config[product]["taxrate"] = 7
                statement_config[product]["cloud_price_incl_refund_net"] = round(statement_config[product]["cloud_price_incl_refund"] / (1 + statement_config[product]["taxrate"] / 100), 2)
                if product == "lightcloud" and statement_config[product]["extra_price_per_kwh"] < 0.3379:
                    if statement_config.get("cloud_number").find("Custom") < 0:
                        statement_config[product]["extra_price_per_kwh"] = 0.3379
                if product.find("consumer") >= 0:
                    if manuell_data.get(f"consumer_extra_price_per_kwh") not in [None, ""]:
                        statement_config[product]["extra_price_per_kwh"] = float(manuell_data.get(f"consumer_extra_price_per_kwh")) / 100
                        statement_config["consumer_data"]["extra_price_per_kwh"] = float(manuell_data.get(f"consumer_extra_price_per_kwh")) / 100
                else:
                    if manuell_data.get(f"{product}_extra_price_per_kwh") not in [None, ""]:
                        statement_config[product]["extra_price_per_kwh"] = float(manuell_data.get(f"{product}_extra_price_per_kwh")) / 100
                if statement["extra_price_per_kwh"] < statement_config[product]["extra_price_per_kwh"]:
                    statement["extra_price_per_kwh"] = statement_config[product]["extra_price_per_kwh"]
                product_delivery_begin = f"{year}-01-01"
                if parse(statement_config[product].get("delivery_begin")).year == year:
                    product_delivery_begin = parse(statement_config[product].get("delivery_begin"))
                if normalize_date(delivery_begin) > normalize_date(product_delivery_begin):
                    product_delivery_begin = delivery_begin
                statement_config[product]["delivery_begin"] = str(product_delivery_begin)
                statement_config[product]["delivery_end"] = str(delivery_end)
                if normalize_date(statement_config[product]["delivery_begin"]) < normalize_date(statement_config["delivery_begin"]):
                    diff_year = calculate_year_diff(statement_config["delivery_begin"], statement_config[product]["delivery_end"], manuell_data.get("corrected_datediff"))
                else:
                    diff_year = calculate_year_diff(statement_config[product]["delivery_begin"], statement_config[product]["delivery_end"], manuell_data.get("corrected_datediff"))
                statement_config[product]["allowed_usage"] = statement_config[product]["usage"] * diff_year

                if product == "lightcloud" and config.get("emove") is not None:
                    statement_config[product]["cloud_price_incl_refund"] = statement_config[product]["cloud_price_incl_refund"] + statement_config["emove"]["cloud_price_incl_refund"]
                    statement_config[product]["label"] = statement_config[product]["label"] + " inkl. eMove"
                    statement_config[product]["allowed_usage_emove"] = float(statement_config["emove"]["usage"]) * diff_year
                    statement_config[product]["allowed_usage"] = statement_config[product]["allowed_usage"] + statement_config[product]["allowed_usage_emove"]
                statement_config[product]["actual_usage"] = 0
                statement_config[product]["actual_usage_net"] = 0
                if (statement_config[product].get("smartme_number") not in empty_values or statement_config[product].get("additional_smartme_numbers") not in empty_values) and (product != "heatcloud" or statement_config.get("measuring_concept") not in ["parallel_concept"] or manuell_data.get("parallel_concept_counter") in ["smartme"]):
                    numbers = [statement_config[product].get("smartme_number")]
                    if statement_config[product].get("additional_smartme_numbers") is not None:
                        numbers = numbers + statement_config[product].get("additional_smartme_numbers")
                    values = []
                    for number in numbers:
                        counter_numbers.append(number)
                        beginning_of_year = get_device_by_datetime(number, statement_config[product]["delivery_begin"])
                        end_of_year = get_device_by_datetime(number, statement_config[product]["delivery_end"])
                        if beginning_of_year is not None and end_of_year is not None:
                            if normalize_date(beginning_of_year.get("Date")) > datetime.datetime(2002,1,1):
                                values.append({
                                    "number": number,
                                    "date": normalize_date(beginning_of_year.get("Date")),
                                    "value": abs(beginning_of_year.get("CounterReading", 0)),
                                    "account": beginning_of_year.get("account"),
                                    "device_label": beginning_of_year.get("device_label"),
                                    "origin": "smartme"
                                })
                            if normalize_date(end_of_year.get("Date")) > datetime.datetime(2002,1,1):
                                values.append({
                                    "number": number,
                                    "date": normalize_date(end_of_year.get("Date")),
                                    "value": abs(end_of_year.get("CounterReading", 0)),
                                    "account": end_of_year.get("account"),
                                    "device_label": end_of_year.get("device_label"),
                                    "origin": "smartme"
                                })
                            statement["available_values"] = statement["available_values"] + values

                    if statement["construction_date"] not in [None, ""] and normalize_date(statement["construction_date"]) > normalize_date(statement_config[product]["delivery_begin"]) and normalize_date(statement["construction_date"]).year == year:
                        counters = normalize_counter_values(
                            statement_config[product]["delivery_begin"],
                            statement["construction_date"],
                            numbers,
                            values.copy(),
                            manuell_data,
                            combine_counters=True
                        )
                        counters2 = normalize_counter_values(
                            statement["construction_date"],
                            statement_config[product]["delivery_end"],
                            numbers,
                            values.copy(),
                            manuell_data,
                            combine_counters=True
                        )
                        if counters is not None and counters2 is not None:
                            counters = counters + counters2
                        elif counters2 is not None:
                            counters = counters2
                    else:
                        counters = normalize_counter_values(
                            statement_config[product]["delivery_begin"],
                            statement_config[product]["delivery_end"],
                            numbers,
                            values.copy(),
                            manuell_data
                        )
                    if counters is not None and len(counters) > 0:
                        statement_config[product]["actual_usage"] = statement_config[product]["actual_usage"] + sum(item['usage'] for item in counters)
                        statement["counters"] = statement["counters"] + counters
                if statement_config[product].get("power_meter_number") not in [None, "", 0, "0"]:
                    counter_numbers.append(statement_config[product].get("power_meter_number"))
                    counter_numbers = counter_numbers + statement_config[product].get("additional_power_meter_numbers", [])
                    values = []
                    for value in statement["available_values"]:
                        if value["number"] == statement_config[product].get("power_meter_number") or value["number"] in statement_config[product].get("additional_power_meter_numbers", []):
                            values.append(value)
                    if product == "lightcloud" and "heatcloud" in statement_config and normalize_date(statement_config["lightcloud"]["delivery_begin"]) != normalize_date(statement_config["heatcloud"]["delivery_begin"]) and statement_config.get("measuring_concept") not in ["parallel_concept"]:
                        counters = normalize_counter_values(
                            statement_config["lightcloud"]["delivery_begin"],
                            statement_config["heatcloud"]["delivery_begin"],
                            [statement_config[product].get("power_meter_number")] + statement_config[product].get("additional_power_meter_numbers", []),
                            values.copy(),
                            manuell_data
                        )
                        counters2 = normalize_counter_values(
                            statement_config["heatcloud"]["delivery_begin"],
                            statement_config["lightcloud"]["delivery_end"],
                            [statement_config[product].get("power_meter_number")] + statement_config[product].get("additional_power_meter_numbers", []),
                            values.copy(),
                            manuell_data
                        )
                        if counters is not None and len(counters) > 0 and counters2 is not None and len(counters2) > 0 and manuell_data.get("hide_netusage") not in [1, True, "1", "true"]:
                            statement_config[product]["actual_usage_net"] = sum(item['usage'] for item in counters2)
                            statement_config["heatcloud"]["actual_usage_net"] = statement_config["heatcloud"]["actual_usage_net"] - statement_config[product]["actual_usage_net"]
                            statement_config[product]["actual_usage_net"] = statement_config[product]["actual_usage_net"] + sum(item['usage'] for item in counters)
                            statement["counters"] = statement["counters"] + counters
                            statement["counters"] = statement["counters"] + counters2
                    else:
                        if product in ["lightcloud", "heatcloud"] and statement["construction_date"] not in [None, ""] and normalize_date(statement["construction_date"]) > normalize_date(statement_config[product]["delivery_begin"]):
                            counters = normalize_counter_values(
                                statement_config[product]["delivery_begin"],
                                statement["construction_date"],
                                [statement_config[product].get("power_meter_number")] + statement_config[product].get("additional_power_meter_numbers", []),
                                values.copy(),
                                manuell_data
                            )
                            counters2 = normalize_counter_values(
                                statement["construction_date"],
                                statement_config[product]["delivery_end"],
                                [statement_config[product].get("power_meter_number")] + statement_config[product].get("additional_power_meter_numbers", []),
                                values.copy(),
                                manuell_data
                            )
                            if counters is None and counters2 is not None:
                                statement_config[product]["actual_usage_net"] = statement_config[product]["actual_usage_net"] + sum(item['usage'] for item in counters2)
                                if product in ["ecloud"] + customer_products:
                                    statement_config[product]["actual_usage"] = statement_config[product]["actual_usage_net"]
                                if counters2 is not None and manuell_data.get("hide_netusage") not in [1, True, "1", "true"]:
                                    statement["counters"] = statement["counters"] + counters2
                            if counters is not None and counters2 is None:
                                statement_config[product]["actual_usage"] = statement_config[product]["actual_usage"] + sum(item['usage'] for item in counters)
                                statement["counters"] = statement["counters"] + counters
                            if counters is not None and len(counters) > 0 and counters2 is not None and len(counters2) > 0:
                                statement_config[product]["actual_usage"] = statement_config[product]["actual_usage"] + sum(item['usage'] for item in counters)
                                statement_config[product]["actual_usage_net"] = statement_config[product]["actual_usage_net"] + sum(item['usage'] for item in counters) + sum(item['usage'] for item in counters2)
                                statement["counters"] = statement["counters"] + counters
                                if product in ["ecloud"] + customer_products:
                                    statement_config[product]["actual_usage"] = statement_config[product]["actual_usage_net"]
                                if counters2 is not None and manuell_data.get("hide_netusage") not in [1, True, "1", "true"]:
                                    statement["counters"] = statement["counters"] + counters2
                                if product == "heatcloud" and statement_config.get("measuring_concept") in ["parallel_concept"] and manuell_data.get("parallel_concept_counter") not in ["smartme"]:
                                    statement_config[product]["actual_usage"] = statement_config[product]["actual_usage_net"]
                        else:
                            if product == "heatcloud" and statement_config.get("measuring_concept") in ["parallel_concept"] and manuell_data.get("parallel_concept_counter") in ["smartme"]:
                                pass
                            else:
                                counters = normalize_counter_values(
                                    statement_config[product]["delivery_begin"],
                                    statement_config[product]["delivery_end"],
                                    [statement_config[product].get("power_meter_number")] + statement_config[product].get("additional_power_meter_numbers", []),
                                    values.copy(),
                                    manuell_data
                                )
                                if product == "lightcloud" or (product == "heatcloud" and (manuell_data.get("parallel_concept_counter") in ["smartme"] or statement_config.get("measuring_concept") not in ["parallel_concept"])):
                                    if manuell_data.get("estimate_netusage") in [1, True, "1", "true"]:
                                        statement["estimate_netusage"] = True
                                        if statement.get("total_self_usage") in [None, ""]:
                                            statement["total_self_usage"] = 0
                                        if statement.get(f"total_self_usage_{product}") in [None, ""]:
                                            statement[f"total_self_usage_{product}"] = 0
                                        statement_config[product]["actual_usage_net"] = statement_config[product]["actual_usage"] * (1 - int(manuell_data.get(f"assumed_autocracy_{product}")) / 100)
                                    else:
                                        if counters is not None and len(counters) > 0:
                                            if manuell_data.get("hide_netusage") not in [1, True, "1", "true"]:
                                                statement_config[product]["actual_usage_net"] = sum(item['usage'] for item in counters)
                                                statement["counters"] = statement["counters"] + counters
                                else:
                                    if counters is not None and len(counters) > 0:
                                        statement_config[product]["actual_usage"] = sum(item['usage'] for item in counters)
                                        statement_config[product]["actual_usage_net"] = sum(item['usage'] for item in counters)
                                        statement["counters"] = statement["counters"] + counters
                    if product in ["lightcloud", "heatcloud"] and manuell_data.get("estimate_netusage") in [1, True, "1", "true"]:
                        if manuell_data.get(f"assumed_autocracy_{product}") is not None:
                            statement["estimate_netusage"] = True
                            if statement.get("total_self_usage") in [None, ""]:
                                statement["total_self_usage"] = 0
                            if statement.get(f"total_self_usage_{product}") in [None, ""]:
                                statement[f"total_self_usage_{product}"] = 0
                            statement_config[product]["actual_usage_net"] = statement_config[product]["actual_usage"] * (1 - int(manuell_data.get(f"assumed_autocracy_{product}")) / 100)

                if product == "heatcloud" and statement_config.get("measuring_concept") in ["parallel_concept"]:
                    statement_config[product]["actual_usage_net"] = statement_config[product]["actual_usage"]
                percent_year = calculate_year_diff(statement_config[product]["delivery_begin"], statement_config[product]["delivery_end"], manuell_data.get("corrected_datediff"))
                statement_config[product]["total_cloud_price"] = statement_config[product]["cloud_price"] * 12 * percent_year
                statement_config[product]["total_cloud_price_net"] = statement_config[product]["total_cloud_price"] / (1 + statement_config["taxrate"] / 100)
                statement_config[product]["total_cloud_price_incl_refund"] = statement_config[product]["cloud_price_incl_refund"] * 12 * percent_year
                statement_config[product]["total_cloud_price_incl_refund_net"] = statement_config[product]["total_cloud_price_incl_refund"] / (1 + statement_config["taxrate"] / 100)
                statement_config[product]["extra_price_per_kwh_net"] = statement_config[product]["extra_price_per_kwh"] / (1 + statement_config["taxrate"] / 100)
                statement_config[product]["percent_year"] = percent_year
                statement_config["percent_year"] = percent_year
                statement_config[product]["total_extra_usage"] = statement_config[product]["actual_usage"] - statement_config[product]["allowed_usage"]
                statement_config[product]["total_extra_price"] = 0
                if product == "ecloud":
                    statement_config[product]["cashback_price_per_kwh"] = statement_config["ecloud_cashback_price_per_kwh"]
                else:
                    statement_config[product]["cashback_price_per_kwh"] = statement_config["cashback_price_per_kwh"]

                statement_config[product]["extra_usage_buffer"] = 250
                if manuell_data.get("corrected_250kwh") not in [None, "", 0, False, "false"]:
                    statement_config[product]["extra_usage_buffer"] = round(250 * percent_year)
                if statement_config[product]["total_extra_usage"] < -statement_config[product]["extra_usage_buffer"]:
                    statement_config[product]["total_extra_price"] = (statement_config[product]["total_extra_usage"] + statement_config[product]["extra_usage_buffer"]) * statement_config[product]["cashback_price_per_kwh"]

                elif statement_config[product]["total_extra_usage"] > 0:
                    statement_config[product]["total_extra_price"] = statement_config[product]["total_extra_usage"] * statement_config[product]["extra_price_per_kwh"]
                statement_config[product]["total_extra_price_net"] = round(statement_config[product]["total_extra_price"] / (1 + statement_config[product]["taxrate"] / 100), 2)

                if statement["taxrate"] != statement_config[product]["taxrate"]:
                    if product == "ecloud" and normalize_date(statement_config[product]["delivery_begin"]) < normalize_date("2022-10-01"):
                        months_running = calculate_year_diff(statement_config[product]["delivery_begin"], "2022-12-31", manuell_data.get("corrected_datediff"))
                        percent_full_tax = calculate_year_diff(statement_config[product]["delivery_begin"], "2022-09-30", manuell_data.get("corrected_datediff")) / months_running
                        statement_config[product]["parts"] = []
                        statement_config[product]["parts"].append({
                            "delivery_begin": statement_config[product]["delivery_begin"],
                            "delivery_end": "2022-09-30",
                            "percent_year": percent_full_tax * months_running,
                            "taxrate": statement["taxrate"],
                            "total_cloud_price": statement_config[product]["total_cloud_price"],
                            "total_cloud_price_incl_refund_net": statement_config[product]["total_cloud_price_incl_refund_net"] * percent_full_tax,
                            "total_cloud_price_incl_refund": statement_config[product]["total_cloud_price_incl_refund"] * percent_full_tax,
                            "extra_price_per_kwh": statement_config[product]["extra_price_per_kwh"],
                            "total_extra_usage": statement_config[product]["total_extra_usage"] * percent_full_tax,
                            "total_extra_price_net": statement_config[product]["total_extra_price_net"] * percent_full_tax,
                            "total_extra_price": statement_config[product]["total_extra_price"] * percent_full_tax,
                            "extra_usage_buffer": statement_config[product]["extra_usage_buffer"] * percent_full_tax,
                            "cashback_price_per_kwh": statement_config[product]["cashback_price_per_kwh"],
                        })
                        half_tax = {
                            "delivery_begin": "2022-10-01",
                            "delivery_end": "2022-12-31",
                            "percent_year": 3 / 12,
                            "taxrate": statement_config[product]["taxrate"],
                            "total_cloud_price": round((statement_config[product]["total_cloud_price_net"] * (1 - percent_full_tax)) * (1 + statement_config[product]["taxrate"] / 100), 4),
                            "total_cloud_price_incl_refund_net": statement_config[product]["total_cloud_price_incl_refund_net"] * (1 - percent_full_tax),
                            "total_cloud_price_incl_refund": round(statement_config[product]["total_cloud_price_incl_refund_net"] * (1 - percent_full_tax) * (1 + statement_config[product]["taxrate"] / 100), 4),
                            "extra_price_per_kwh": round(statement_config[product]["extra_price_per_kwh_net"] * (1 + statement_config[product]["taxrate"] / 100), 4),
                            "total_extra_usage": statement_config[product]["total_extra_usage"] * (1 - percent_full_tax),
                            "extra_usage_buffer": statement_config[product]["extra_usage_buffer"] * (1 - percent_full_tax),
                            "cashback_price_per_kwh": round((statement_config[product]["cashback_price_per_kwh"] / (1 + statement["taxrate"] / 100)) * (1 + statement_config[product]["taxrate"] / 100), 4)
                        }
                        if half_tax["total_extra_usage"] > 0:
                            half_tax["total_extra_price"] = half_tax["total_extra_usage"] * half_tax["extra_price_per_kwh"]
                        else:
                            half_tax["total_extra_price"] = half_tax["total_extra_usage"] * half_tax["cashback_price_per_kwh"]
                        half_tax["total_extra_price_net"] = half_tax["total_extra_price"] / (1 + statement_config[product]["taxrate"] / 100)
                        statement_config[product]["parts"].append(half_tax)
                        statement_config[product]["total_cloud_price_incl_refund"] = statement_config[product]["parts"][0]["total_cloud_price_incl_refund"] + statement_config[product]["parts"][1]["total_cloud_price_incl_refund"]
                        statement_config[product]["total_extra_price_net"] = statement_config[product]["parts"][0]["total_extra_price_net"] + statement_config[product]["parts"][1]["total_extra_price_net"]
                        statement_config[product]["total_extra_price"] = statement_config[product]["parts"][0]["total_extra_price"] + statement_config[product]["parts"][1]["total_extra_price"]
                    else:
                        statement_config[product]["total_cloud_price_incl_refund"] = round(statement_config[product]["total_cloud_price_incl_refund_net"] * (1 + statement_config[product]["taxrate"] / 100), 4)
                    statement_config[product]["total_cloud_price"] = round(statement_config[product]["total_cloud_price_net"] * (1 + statement_config[product]["taxrate"] / 100), 4)
                    statement_config[product]["extra_price_per_kwh"] = round(statement_config[product]["extra_price_per_kwh_net"] * (1 + statement_config[product]["taxrate"] / 100), 4)

                if product == "ecloud" and str(year) == "2022":
                    statement["has_ecloud_tax_reduction"] = True
                    statement_config[product]["special_refund"] = {
                        "label": "Dezember Hilfe Gas",
                        "percent_year": 1/12,
                        "taxrate": 7,
                        "total": -(statement_config[product]["usage"] * 1/12 * statement_config[product]["extra_price_per_kwh"] + statement_config[product]["cloud_price"])
                    }
                    statement_config[product]["special_refund"]["total_net"] = statement_config[product]["special_refund"]["total"] / (1 + statement_config[product]["special_refund"]["taxrate"] / 100)
                    statement_config["total_cloud_price"] = statement_config["total_cloud_price"] + statement_config[product]["special_refund"]["total"]
                    statement_config["total_cloud_price_net"] = statement_config["total_cloud_price_net"] + statement_config[product]["special_refund"]["total_net"]
                    statement_config["total_cloud_price_incl_refund"] = statement_config["total_cloud_price_incl_refund"] + statement_config[product]["special_refund"]["total"]
                    statement_config["total_cloud_price_incl_refund_net"] = statement_config["total_cloud_price_incl_refund_net"] + statement_config[product]["special_refund"]["total_net"]
                statement_config["total_cloud_price"] = statement_config["total_cloud_price"] + statement_config[product]["cloud_price_incl_refund"] * 12 * percent_year
                statement_config["total_cloud_price_net"] = statement_config["total_cloud_price_net"] + statement_config[product]["cloud_price_incl_refund_net"] * 12 * percent_year
                statement_config["total_cloud_price_incl_refund"] = statement_config["total_cloud_price_incl_refund"] + statement_config[product]["total_cloud_price_incl_refund"]
                statement_config["total_cloud_price_incl_refund_net"] = statement_config["total_cloud_price_incl_refund_net"] + statement_config[product]["total_cloud_price_incl_refund_net"]
                statement_config["total_extra_price"] = statement_config["total_extra_price"] + statement_config[product]["total_extra_price"]
                statement_config["total_extra_price_net"] = statement_config["total_extra_price_net"] + statement_config[product]["total_extra_price_net"]
                statement_config["total_extra_usage"] = statement_config["total_extra_usage"] + statement_config[product]["total_extra_usage"]
                statement_config["total_usage"] = statement_config["total_usage"] + statement_config[product]["actual_usage"]
            statement["total_usage"] = statement["total_usage"] + statement_config["total_usage"]
            statement["total_extra_usage"] = statement["total_extra_usage"] + statement_config["total_extra_usage"]
            statement["total_cloud_price"] = statement["total_cloud_price"] + statement_config["total_cloud_price"]
            statement["total_cloud_price_net"] = statement["total_cloud_price_net"] + statement_config["total_cloud_price_net"]
            statement["total_cloud_price_incl_refund"] = statement["total_cloud_price_incl_refund"] + statement_config["total_cloud_price_incl_refund"]
            statement["total_cloud_price_incl_refund_net"] = statement["total_cloud_price_incl_refund_net"] + statement_config["total_cloud_price_incl_refund_net"]
            statement["total_extra_price"] = statement["total_extra_price"] + statement_config["total_extra_price"]
            statement["total_extra_price_net"] = statement["total_extra_price_net"] + statement_config["total_extra_price_net"]

            statement_config["consumers"] = []
            for customer_product in customer_products:
                if statement_config.get(customer_product) is None:
                    continue
                statement_config["consumers"].append(statement_config[customer_product])
            for product in ["heatcloud", "lightcloud", "ecloud"] + customer_products:
                if product not in statement_config:
                    continue
                if statement_config[product]["actual_usage"] <= 0:
                    statement["errors"].append(f"{statement_config[product]['label']} hat keinen Verbrauch")
                if statement_config[product]["actual_usage"] < statement_config[product]["actual_usage_net"]:
                    statement["warnings"].append(f"{statement_config[product]['label']} Netzbezug ist größer als der Gesamtverbrauch")
                if statement_config[product]["actual_usage"] > 0 and statement_config[product]["actual_usage_net"]/statement_config[product]["actual_usage"] > 0.8 and product not in customer_products:
                    statement["warnings"].append(f"{statement_config[product]['label']} Netzbezug ist mehr als 80% vom Gesamtverbrauch")
                if product == "lightcloud" and statement_config[product]["actual_usage_net"] <= 0:
                    statement["warnings"].append(f"{statement_config[product]['label']} Netzbezug ist nicht vorhanden")
            statement["configs"].append(statement_config)
    statement["total_self_usage"] = 0
    for product in ["heatcloud", "lightcloud", "ecloud"] + customer_products:
        for statement_config in statement["configs"]:
            if product not in statement_config:
                continue
            if statement_config[product].get("actual_usage_net") in [None, "", 0]:
                continue
            if f"total_self_usage_{product}" not in statement:
                statement[f"total_self_usage_{product}"] = 0
            statement[f"total_self_usage_{product}"] = statement[f"total_self_usage_{product}"] + statement_config[product]["actual_usage"] - statement_config[product]["actual_usage_net"]
            statement["total_self_usage"] = statement["total_self_usage"] + statement_config[product]["actual_usage"] - statement_config[product]["actual_usage_net"]

    odoo_payment_amount = get_payments_by_contract(data.get("contract_number"), normalize_date(statement["delivery_begin"]), normalize_date(statement["delivery_end"]))
    if data.get("fakturia") is not None and data.get("fakturia").get("contractStatus") not in ["ENDED"]:
        statement["is_fakturia"] = True
        statement["payments"] = []
        statement["pre_payments_total"] = 0
        for payment in data.get("invoices_credit_notes"):
            if payment["date"][:4] == str(year) and payment["amountGross_normalized_prepay"] != 0:
                statement["pre_payments_total"] = statement["pre_payments_total"] + payment["amountGross_normalized_prepay"]
                statement["payments"].append(payment)
        if odoo_payment_amount is not None:
            statement["pre_payments_total"] = statement["pre_payments_total"] + odoo_payment_amount
            statement["payments"] = None
    else:
        statement["pre_payments_total"] = statement["total_cloud_price_incl_refund"]
        if odoo_payment_amount is not None:
            statement["pre_payments_total"] = odoo_payment_amount
    if manuell_data.get("paid_amount_overwrite") not in [None, ""]:
        statement["pre_payments_total"] = float(manuell_data.get("paid_amount_overwrite"))
        statement["payments"] = None
    statement["extra_credit_value"] = 0
    statement["extra_credit_label"] = ""
    if manuell_data.get("extra_credit_value") not in [None, "", 0]:
        statement["extra_credit_label"] = manuell_data.get("extra_credit_label")
        statement["extra_credit_value"] = -float(manuell_data.get("extra_credit_value"))
    statement["extra_credit_value_net"] =  statement["extra_credit_value"] / (1 + statement["taxrate"] / 100)
    statement["extra_credit_value2"] = 0
    statement["extra_credit_label2"] = ""
    if manuell_data.get("extra_credit_value2") not in [None, "", 0]:
        statement["extra_credit_label2"] = manuell_data.get("extra_credit_label2")
        statement["extra_credit_value2"] = -float(manuell_data.get("extra_credit_value2"))
    statement["extra_credit_value2_net"] =  statement["extra_credit_value2"] / (1 + statement["taxrate"] / 100)
    statement["cost_total"] = statement["total_cloud_price_incl_refund"] + statement["total_extra_price"] + statement["extra_credit_value"] + statement["extra_credit_value2"]
    statement["to_pay"] = statement["total_cloud_price_incl_refund"] - statement["pre_payments_total"] + statement["total_extra_price"] + statement["extra_credit_value"] + statement["extra_credit_value2"]
    statement["to_pay_net"] = statement["to_pay"] / 1.19
    for value in statement["available_values"]:
        value["date"] = str(value["date"])
    statement["manuell_counter_values"] = []
    for counter_number in counter_numbers:
        values = CounterValue.query.filter(CounterValue.number == counter_number).order_by(CounterValue.date.asc()).all()
        for value in values:
            statement["manuell_counter_values"].append({
                "id": value.id,
                "number": str(value.number),
                "date": value.date.strftime("%Y-%m-%d"),
                "value": value.value,
                "origin": value.origin
            })

    return json.loads(json.dumps(statement))

    if pv_usage is not None:
        statement["pv_system"]["begin"] = pv_usage["start_date"]
        statement["pv_system"]["end"] = pv_usage["end_date"]
        statement["pv_system"]["total_usage"] = int(pv_usage["usage"])
        statement["counters"].append(pv_usage)

    if data["pv_system"].get("heatcloud_usages") not in [None, "", 0]:
        pv_heatcloud_usage = next((item for item in data["pv_system"]["heatcloud_usages"] if item["year"] == year), None)
        if pv_heatcloud_usage is not None:
            statement["pv_system"]["begin_heatcloud"] = pv_heatcloud_usage["start_date"]
            statement["pv_system"]["end_heatcloud"] = pv_heatcloud_usage["end_date"]
            statement["pv_system"]["total_usage_heatcloud"] = int(pv_heatcloud_usage["usage"])
    statement["pv_system"]["direct_usage"] = statement["pv_system"]["total_usage"] - statement["pv_system"]["cloud_usage"]
    if data.get("lightcloud") is None:
        return statement
    lightcloud_begin = None
    if data["lightcloud"].get("delivery_begin") not in ["", None, 0, "0"]:
        lightcloud_begin = parse(data["lightcloud"]["delivery_begin"])
        if lightcloud_begin.year < year:
            lightcloud_begin = parse(f"{year}-01-01")
    lightcloud_end = parse(f"{year}-12-31")
    if data["lightcloud"].get("cancelation_due_date") not in ["", None, 0, "0"]:
        enddate = parse(data["lightcloud"]["cancelation_due_date"])
        if enddate.year == year:
            lightcloud_end = enddate
    statement["lightcloud"] = {
        "begin": str(lightcloud_begin),
        "end": str(lightcloud_end),
        "year_percent": (diff_month(lightcloud_end, lightcloud_begin) / 12),
        "extra_price_per_kwh": 0.3379,
        "cashback_per_kwh": 0.10,
        "price_per_month": data["cloud"]["cloud_monthly_price"]
    }
    statement["lightcloud"]["included_usage"] = int(int(data["lightcloud"]["usage"]) * statement["lightcloud"]["year_percent"])
    statement["lightcloud"]["price"] = statement["lightcloud"]["price_per_month"] * 12 * statement["lightcloud"]["year_percent"]
    if data["emove"] is not None:
        statement["emove"] = {
            "packet": data["emove"]["packet"],
            "begin": str(lightcloud_begin),
            "end": str(lightcloud_end),
            "year_percent": (diff_month(lightcloud_end, lightcloud_begin) / 12),
            "extra_price_per_kwh": 0.3379,
            "price_per_month": 0
        }
        statement["emove"]["included_usage"] = int(int(data["emove"]["usage_inhouse"]) * statement["emove"]["year_percent"])
        statement["emove"]["price"] = statement["emove"]["price_per_month"] * 12 * statement["emove"]["year_percent"]

    pv_end = normalize_date(statement["pv_system"].get("end"))
    if normalize_date(lightcloud_end) > pv_end:
        days_to_add = (lightcloud_end - pv_end).days
        pv_begin = normalize_date(statement["pv_system"].get("begin"))
        days_recorded = (pv_end - pv_begin).days
        usage_per_day = statement["pv_system"].get("total_usage") / days_recorded
        statement["pv_system"]["end"] = str(lightcloud_end)
        statement["pv_system"]["total_usage"] = statement["pv_system"]["total_usage"] + usage_per_day * days_to_add
        statement["pv_system"]["direct_usage"] = statement["pv_system"]["total_usage"] - statement["pv_system"]["cloud_usage"]

    if status is not None and status.manuell_data is not None:
        if status.manuell_data.get("senec_direct_usage") not in [None, 0]:
            statement["pv_system"]["direct_usage"] = int(status.manuell_data.get("senec_direct_usage")) + int(status.manuell_data.get("senec_storage_usage"))
        statement["pv_system"]["begin"] = str(lightcloud_begin)
        statement["pv_system"]["end"] = str(lightcloud_end)
        statement["pv_system"]["total_usage"] = statement["pv_system"]["cloud_usage"] + statement["pv_system"]["direct_usage"]
        if status.manuell_data.get("extra_price_per_kwh") not in [None, 0, "", "0"]:
            statement["lightcloud"]["extra_price_per_kwh"] = float(status.manuell_data.get("extra_price_per_kwh"))
    statement["total_extra_usage"] = statement["pv_system"]["total_usage"] - statement["lightcloud"]["included_usage"]
    if statement.get("emove") is not None:
        statement["total_extra_usage"] = statement["total_extra_usage"] - statement["emove"]["included_usage"]
    if statement["total_extra_usage"] > 0:
        statement["total_extra_usage_price"] = statement["total_extra_usage"] * statement["lightcloud"]["extra_price_per_kwh"]
    else:
        if statement["total_extra_usage"] < -250:
            statement["total_extra_usage_price"] = (statement["total_extra_usage"] + 250) * statement["lightcloud"]["cashback_per_kwh"]
        else:
            statement["total_extra_usage_price"] = 0
    statement["pre_payments"] = []
    if len(data["payments"].get("invoices")) > 0 or len(data["payments"].get("credit_notes")) > 0:
        statement["to_pay"] = statement["lightcloud"]["price"] + statement["total_extra_usage_price"]
        if len(data["payments"].get("invoices")) > 0:
            for invoice in data["payments"].get("invoices"):
                if invoice.get("canceled") in [True, "true"]:
                    continue
                invoice_date = parse(invoice['date'])
                if invoice['amountGross'] != 0 and str(invoice_date.year) == str(year):
                    statement["pre_payments"].append({
                        "label": f"Vorauszahlungen {invoice['number']}",
                        "begin": str(invoice['date']),
                        "end": "",
                        "price": invoice['amountGross']
                    })
                    statement["to_pay"] = statement["to_pay"] - invoice['amountGross']
        if len(data["payments"].get("credit_notes")) > 0:
            for invoice in data["payments"].get("credit_notes"):
                if invoice.get("canceled") in [True, "true"]:
                    continue
                invoice_date = parse(invoice['date'])
                if invoice['amountGross'] != 0 and str(invoice_date.year) == str(year):
                    statement["pre_payments"].append({
                        "label": f"Auszahlung {invoice['number']}",
                        "begin": str(invoice['date']),
                        "end": "",
                        "price": -invoice['amountGross']
                    })
                    statement["to_pay"] = statement["to_pay"] + invoice['amountGross']
    if len(statement["pre_payments"]) == 0:
        statement["pre_payments"].append({
            "label": "Vorauszahlungen",
            "begin": str(lightcloud_begin),
            "end": str(lightcloud_end),
            "price": statement["lightcloud"]["price"]
        })
        statement["to_pay"] = statement["total_extra_usage_price"]
    return statement

def normalize_contract_number(cloud_contract_number):
    if cloud_contract_number in [None, "None", "", 0, "0"]:
        return None
    number = re.findall(r'C[0-9]+', cloud_contract_number)
    if len(number) > 0:
        return number[0]
    return cloud_contract_number


def get_item_status(deal):
    if deal.get("cloud_delivery_begin") in [None, "", 0, "0"]:
        return "not started"
    delivery_begin = parse(deal.get("cloud_delivery_begin"))
    cancelation_due_date = None
    if deal.get("cancelation_due_date") not in [None, "", 0, "0"]:
        cancelation_due_date = parse(deal.get("cancelation_due_date"))
    if cancelation_due_date is not None and cancelation_due_date < datetime.datetime.utcnow().replace(tzinfo=pytz.utc):
        return "canceled"
    if delivery_begin < datetime.datetime.utcnow().replace(tzinfo=pytz.utc):
        return "active"
    return "waiting"


def diff_month(d1, d2):
    if d1 is None or d2 is None:
        return 0
    months = (d1.year - d2.year) * 12 + d1.month - d2.month
    _null, last_day = calendar.monthrange(d1.year, d1.month)
    months = months + (1 - (d1.day - 1) / (last_day - 1))
    _null, last_day = calendar.monthrange(d2.year, d2.month)
    months = months + (1 - (d2.day - 1) / (last_day - 1))
    return months


def generate_annual_report(contract_number, year):

    data = get_contract_data(contract_number)

    contract_status = ContractStatus.query.filter(ContractStatus.year == str(year)).filter(ContractStatus.contract_number == contract_number).first()

    if contract_status.manuell_data is None:
        contract_status.manuell_data = {}
    if contract_status.manuell_data.get("assumed_autocracy_lightcloud") in [None, "", 0, "0"]:
        contract_status.manuell_data["assumed_autocracy_lightcloud"] = 50
    if contract_status.manuell_data.get("assumed_autocracy_heatcloud") in [None, "", 0, "0"]:
        contract_status.manuell_data["assumed_autocracy_heatcloud"] = 28
    statement = get_annual_statement_data(data, year, contract_status.manuell_data)
    contract_status.data = statement
    db.session.commit()
    return data


def generate_annual_report_pdf(contract_number, year):
    config = get_settings(section="external/bitrix24")

    data = get_contract_data(contract_number)

    contract_status = ContractStatus.query.filter(ContractStatus.year == str(year)).filter(ContractStatus.contract_number == contract_number).first()
    statement = contract_status.data
    pdf = generate_annual_statement_pdf(data, contract_status.data)
    subfolder_id = create_folder_path(415280, path=f"Cloud/Kunde {data['contact_id']}/Vertrag {data['contract_number']}")  # https://keso.bitrix24.de/docs/path/Kundenordner/

    statement["drive_id"] = add_file(folder_id=subfolder_id, data={
        "file_content": pdf,
        "filename": f"Cloud Abrechnung {year}.pdf"
    })
    statement["pdf_link"] = get_public_link(statement["drive_id"], expire_minutes=525600)

    status = ContractStatus.query\
        .filter(ContractStatus.contract_number == contract_number)\
        .filter(ContractStatus.year == year)\
        .first()
    if status is None:
        status = ContractStatus(contract_number=contract_number, year=year)
        db.session.add(status)
    status.is_generated = True
    status.pdf_file_id = statement["drive_id"]
    status.pdf_file_link = statement["pdf_link"]
    status.to_pay = statement["to_pay"]
    if contract_number != "":
        deals = get_deals({
            "SELECT": "full",
            f"filter[={config['deal']['fields']['cloud_contract_number']}]": contract_number,
            "filter[CATEGORY_ID]": 126,
        })
        if deals is not None and len(deals) > 0:
            deal_id = deals[0].get("id")
            print(deal_id, {
                # "stage_id": "C126:UC_WT48N4",
                "annual_statement_link": statement["pdf_link"],
                "opportunity": round(statement["to_pay"], 2),
                "annual_report_amount": round(statement["to_pay"], 2),
                "annual_report_begin": str(normalize_date(statement["delivery_begin"])),
                "annual_report_end": str(normalize_date(statement["delivery_end"]))
            })
            update_deal(deal_id, {
                # "stage_id": "C126:UC_WT48N4",
                "annual_statement_link": statement["pdf_link"],
                "opportunity": round(statement["to_pay"], 2),
                "annual_report_amount": round(statement["to_pay"], 2),
                "annual_report_begin": str(normalize_date(statement["delivery_begin"])),
                "annual_report_end": str(normalize_date(statement["delivery_end"]))
            })
    db.session.commit()
    return data


def normalize_date(datetime):
    return parse(parse(str(datetime)).strftime("%Y-%m-%d"))


def normalize_counter_values(start_date, end_date, numbers, values, manuell_data, combine_counters=False):
    counters = []
    start_date = normalize_date(start_date)
    end_date = normalize_date(end_date)
    diff_days_target = (end_date - start_date).days
    for number in numbers:
        if number is None:
            continue
        number = string_stripper(number)
        start_value_earlier = CounterValue.query.filter(CounterValue.number == number)\
            .filter(CounterValue.date <= start_date)\
            .order_by(CounterValue.date.desc()) \
            .limit(1)\
            .all()
        if len(start_value_earlier) > 0:
            values.append({
                "date": normalize_date(start_value_earlier[0].date),
                "number": number,
                "value": start_value_earlier[0].value,
                "origin": start_value_earlier[0].origin
            })
        start_value_later = CounterValue.query.filter(CounterValue.number == number)\
            .filter(CounterValue.date > start_date)\
            .order_by(CounterValue.date.asc()) \
            .limit(1)\
            .all()
        if len(start_value_later) > 0:
            values.append({
                "date": normalize_date(start_value_later[0].date),
                "number": number,
                "value": start_value_later[0].value,
                "origin": start_value_later[0].origin
            })
        end_value_earlier = CounterValue.query.filter(CounterValue.number == number)\
            .filter(CounterValue.date <= end_date)\
            .order_by(CounterValue.date.desc()) \
            .limit(1)\
            .all()
        if len(end_value_earlier) > 0:
            values.append({
                "date": normalize_date(end_value_earlier[0].date),
                "number": number,
                "value": end_value_earlier[0].value,
                "origin": end_value_earlier[0].origin
            })
        end_value_later = CounterValue.query.filter(CounterValue.number == number)\
            .filter(CounterValue.date > end_date)\
            .order_by(CounterValue.date.asc()) \
            .limit(1)\
            .all()
        if len(end_value_later) > 0:
            values.append({
                "date": normalize_date(end_value_later[0].date),
                "number": number,
                "value": end_value_later[0].value,
                "origin": end_value_later[0].origin
            })
        values = sorted(values, key=lambda d: d['date'])
        start_value = None
        start_value2 = None
        end_value = None
        for value in values:
            if string_stripper(value["number"]) == number:
                if value["date"] == start_date:
                    start_value = value
                elif value["date"] < start_date:
                    start_value = value
                elif value["date"] > start_date:
                    if start_value is None:
                        start_value = value
                    elif (start_date - start_value["date"]).days > (value["date"] - start_date).days:
                        start_value2 = copy.deepcopy(start_value)
                        start_value = value
                if value["date"] == start_value["date"]:
                    continue
                if value["date"] == end_date:
                    end_value = value
                elif value["date"] < end_date:
                    end_value = value
                elif value["date"] > end_date:
                    if end_value is None:
                        end_value = value
                    elif (end_value["date"] - start_date).days < diff_days_target * 0.3:
                        end_value = value
                    elif (end_date - end_value["date"]).days > (value["date"] - end_date).days:
                        end_value = value
        if start_value == end_value:
            start_value = start_value2
        if end_value is None:
            end_value = start_value
            start_value = start_value2
        if end_value is None or start_value is None:
            continue
        origin = start_value["origin"]
        if start_value["origin"] != end_value["origin"]:
            origin = f'{start_value["origin"]}/{end_value["origin"]}'
        counters.append({
            "number": number,
            "type": origin,
            "start_date": start_value["date"],
            "start_value": start_value["value"],
            "start_estimated": False,
            "start_account": start_value.get("account"),
            "start_device_label": start_value.get("device_label"),
            "end_date": end_value["date"],
            "end_value": end_value["value"],
            "end_estimated": False,
            "end_account": end_value.get("account"),
            "end_device_label": end_value.get("device_label")
        })
    if len(counters) == 0:
        return None

    average_value_per_day = 0
    for counter_value in counters:
        counter_value["diff_days"] = (counter_value["end_date"] - counter_value["start_date"] ).days
        if counter_value["diff_days"] <= 0:
            counter_value["value_per_day"] = (counter_value["end_value"] - counter_value["start_value"])
        else:
            counter_value["value_per_day"] = (counter_value["end_value"] - counter_value["start_value"]) / counter_value["diff_days"]
        average_value_per_day = average_value_per_day + counter_value["value_per_day"]
    average_value_per_day = average_value_per_day / len(counters)

    counters = sorted(counters, key=lambda d: d["start_date"])

    first_counter = counters[0]
    last_counter = counters[len(counters) - 1]
    diff_days_value = (last_counter["end_date"] - first_counter["start_date"]).days
    if manuell_data.get("skip_counter_date_range_limiter") not in [True, 1, "1", "true"]:
        if diff_days_target < 100:
            if diff_days_target * 0.2 > diff_days_value:
                return None
        else:
            if diff_days_target * 0.3 > diff_days_value:
                return None
    if combine_counters:
        for counter in counters:
            first_counter = counter
            if first_counter["start_date"] != start_date:
                diff_start_days = (first_counter["start_date"] - start_date).days
                first_counter["start_date"] = start_date
                first_counter["start_estimated"] = True
                first_counter["start_value"] = first_counter["start_value"] - diff_start_days * average_value_per_day
                if first_counter["start_value"] < 0:
                    first_counter["start_value"] = 0
            first_counter["usage"] = first_counter["end_value"] - first_counter["start_value"]

            last_counter = counter
            if last_counter["end_date"] != end_date:
                diff_start_days = (last_counter["end_date"] - end_date).days
                last_counter["end_date"] = end_date
                last_counter["end_estimated"] = True
                last_counter["end_value"] = last_counter["end_value"] - diff_start_days * average_value_per_day
                if last_counter["end_value"] < 0:
                    last_counter["end_value"] = 0
            last_counter["usage"] = last_counter["end_value"] - last_counter["start_value"]
    else:
        if first_counter["start_date"] != start_date:
            diff_start_days = (first_counter["start_date"] - start_date).days
            first_counter["start_date"] = start_date
            first_counter["start_estimated"] = True
            first_counter["start_value"] = first_counter["start_value"] - diff_start_days * average_value_per_day
            if first_counter["start_value"] < 0:
                first_counter["start_value"] = 0
        first_counter["usage"] = first_counter["end_value"] - first_counter["start_value"]

        if last_counter["end_date"] != end_date:
            diff_start_days = (last_counter["end_date"] - end_date).days
            last_counter["end_date"] = end_date
            last_counter["end_estimated"] = True
            last_counter["end_value"] = last_counter["end_value"] - diff_start_days * average_value_per_day
            if last_counter["end_value"] < 0:
                last_counter["end_value"] = 0
        last_counter["usage"] = last_counter["end_value"] - last_counter["start_value"]

    for counter in counters:
        counter["start_date"] = str(counter["start_date"])
        counter["end_date"] = str(counter["end_date"])
    return counters


def cron_transfer_fakturia_annual_invoice():
    return
    deals = get_deals({
        "SELECT": "full",
        "filter[CATEGORY_ID]": 126,
        "filter[STAGE_ID]": "C126:UC_L0M7DR"
    }, force_reload=True)
    for deal in deals:
        if float(deal.get("opportunity")) == 0.0:
            update_deal(deal.get("id"), {
                "stage_id": "C126:FINAL_INVOICE"
            })
            continue
        print("deal", deal.get("id"), float(deal.get("opportunity")))
        contract = get_contract_data(deal.get("contract_number"))
        if isinstance(contract.get("fakturia"), list) and len(contract.get("fakturia")) == 0:
            print("orgamaxx")
            update_deal(deal.get("id"), {
                "stage_id": "C126:EXECUTING"
            })
            continue
        if contract.get("fakturia") is not None and contract.get("fakturia").get("contractStatus") in ["ACTIVE", "ENDED"]:
            print("fakturia")
            print(json.dumps(contract, indent=2))
            min_delivery_begin = None
            max_year = 0
            for annual_statement in contract.get("annual_statements"):
                if max_year == 0 or (max_year < annual_statement.get("year") and annual_statement.get("data") is not None and annual_statement.get("pdf_link") is not None):
                    max_year = annual_statement.get("year")
            for config in contract["configs"]:
                if config["delivery_begin"] not in [None, ""] and (min_delivery_begin is None or min_delivery_begin > parse(config["delivery_begin"])):
                    min_delivery_begin = parse(config["delivery_begin"])
                if config.get("earliest_delivery_begin") not in [None, ""] and (min_delivery_begin is None or min_delivery_begin > parse(config["earliest_delivery_begin"])):
                    min_delivery_begin = parse(config["earliest_delivery_begin"])
            payment_data = {
                "itemNumber": "Jahresabrechnung",
                "quantity": 1,
                "individualPrice": float(deal.get("opportunity")) / 1.19,
                "description": f"Jahresabrechnung {max_year} zum Vertrag {deal.get('contract_number')}",
                "performanceDateStart": f"{max_year}-01-01",
                "performanceDateEnd": f"{max_year}-12-31",
                "type": "DEFAULT_PERFORMANCE"
            }
            if min_delivery_begin.year == max_year:
                payment_data["performanceDateStart"] = min_delivery_begin.strftime("%Y-%m-%d")
            if float(deal.get("opportunity")) < 0:
                payment_data["individualPrice"] = payment_data["individualPrice"] * -1
                payment_data["type"] = "REVERSE_PERFORMANCE_OTHER"
            print(json.dumps(payment_data, indent=2))
            generate_invoice(contract.get("fakturia").get("contractNumber"), payment_data)

            update_deal(deal.get("id"), {
                "stage_id": "C126:FINAL_INVOICE"
            })
        else:
            print("orgamaxx")
            update_deal(deal.get("id"), {
                "stage_id": "C126:EXECUTING"
            })


def find_credit_memo_bugs():
    deals = get_deals({
        "SELECT": "full",
        "filter[CATEGORY_ID]": 126,
        "filter[STAGE_ID]": "C126:WON"
    }, force_reload=True)
    deals = deals + get_deals({
        "SELECT": "full",
        "filter[CATEGORY_ID]": 126,
        "filter[STAGE_ID]": "C126:FINAL_INVOICE"
    }, force_reload=True)
    count = 0
    amount = 0
    for deal in deals:
        data = get_contract_data(deal.get("contract_number"))
        if data.get("invoices_credit_notes") not in [None] and len(data.get("invoices_credit_notes")) > 0 and data["invoices_credit_notes"][0]["type"] == "credit_note":
            contract_amount = 0
            for statement in data.get("annual_statements"):
                if statement.get("year") != 2021:
                    continue
                if statement.get("data") is None:
                    continue
                if statement.get("data").get("payments") is None:
                    continue
                for payment in statement.get("data").get("payments"):
                    if payment.get("type") != "credit_note":
                        continue
                    contract_amount = contract_amount + payment.get("amountNet")
            if contract_amount > 30:
                count = count + 1
                print(deal.get("contract_number"))
                print(contract_amount)
                amount = amount + contract_amount
    print(count)
    print(amount)


def add_custom_config(contract_number):
    data = get_contract_data(contract_number)
    if data.get("main_deal") in [None, ""]:
        return False
    offer_v2 = OfferV2()
    offer_v2.datetime = datetime.datetime.now()
    offer_v2.offer_group = "cloud-offer"
    db.session.add(offer_v2)
    db.session.flush()
    offer_v2.number = f"Custom-{offer_v2.id}"
    offer_v2.data = {
        'old_cloud_number': data.get("main_deal").get("cloud_number"),
        "cloud_quote_type": "custom_config",
        "bic": "",
        "iban": "",
        "bankname": "",
        "roofs": [
            { "sqm": 1, "direction": "west_east", "pv_kwp_used": data["main_deal"].get("pv_kwp"), "pv_sqm_used": 1 }
        ],
        "pv_kwp": data["main_deal"].get("pv_kwp"),
        "pv_sqm": 1,
        "address": {
            "name": "",
            "first_name": "",
            "last_name": "",
            "firstname": "",
            "lastname": "",
            "street": "",
            "street_nb": "",
            "zip": "",
            "city": "",
            "email": [{ "VALUE": "", "TYPE_ID": "EMAIL", "VALUE_TYPE": "WORK" }],
            "phone": [{ "VALUE": "", "TYPE_ID": "PHONE", "VALUE_TYPE": "WORK" }]
        },
        "consumers": [],
        "module_kwp": { },
        "emove_tarif": "none",
        "extra_notes": "",
        "power_usage": 1000,
        "cloud_number": offer_v2.number,
        "ecloud_usage": 0,
        "has_pv_quote": True,
        "heater_usage": 0,
        "main_malo_id": "",
        "assigned_user": data.get("main_deal").get("assigned_user"),
        "extra_options": [],
        "financing_bank": "",
        "financing_rate": 4.89,
        "inflation_rate": 1.2,
        "roof_direction": "west_east",
        "investment_type": "financing",
        "is_new_building": False,
        "price_guarantee": "2_years",
        "consumers_ecloud": [],
        "price_increase_rate": 5,
        "consumers_lightcloud": [],
        "conventional_power_cost_per_kwh": 31.0,
        "tax_rate": 19
    }
    offer_v2.calculated = calculate_cloud(data=offer_v2.data)
    items = get_cloud_products(data={"calculated": offer_v2.calculated, "data": offer_v2.data})
    offer_v2.items = []
    for item_data in items:
        item_object = OfferV2Item()
        item_object = set_attr_by_dict(item_object, item_data, ["id"])
        offer_v2.items.append(item_object)
    db.session.commit()
    update_deal(data.get("main_deal").get("id"), {
        "cloud_number": offer_v2.number
    })
    return True


def store_custom_config(data):
    print(json.dumps(data, indent=2))
    if data.get("cloud_number") is None:
        return False
    offer_v2 = OfferV2.query.filter(OfferV2.number == data.get("cloud_number")).first()
    print(offer_v2)
    if offer_v2 is None:
        return False
    offer_data = json.loads(json.dumps(offer_v2.data))
    offer_data["cloud_quote_type"] = "custom_config"
    for product in ["lightcloud", "heatcloud", "ecloud"]:
        if product == "lightcloud":
            usage_key = "power_usage"
        if product == "heatcloud":
            usage_key = "heater_usage"
        if product == "ecloud":
            usage_key = "ecloud_usage"
        if data.get(product) not in [None, ""]:
            offer_data[usage_key] = int(data[product].get("usage"))
        else:
            offer_data[usage_key] = 0
    offer_data["consumers"] = []
    for consumer in data["consumers"]:
        offer_data["consumers"].append({
            "usage": consumer["usage"],
            "address": {}
        })
    offer_data["pv_kwp_overwrite"] = data.get("pv_kwp_overwrite")
    offer_data["pv_kwp"] = data.get("pv_kwp")
    for product in ["lightcloud", "heatcloud", "ecloud"]:
        if data.get(product) is not None:
            offer_data[f"{product}_min_kwp_overwrite"] = data.get(product).get("min_kwp_overwrite")
            if offer_data[f"{product}_min_kwp_overwrite"] is True:
                offer_data[f"{product}_min_kwp"] = data.get(product).get("min_kwp")
    offer_data["consumer_min_kwp_overwrite"] = data.get("consumer_min_kwp_overwrite")
    if offer_data["consumer_min_kwp_overwrite"] is True:
        offer_data["consumer_min_kwp"] = data.get("consumer_min_kwp")
    offer_data["old_price_calculation"] = "VOgcqFFeQLpV9cxOA02lzXdAYX"
    offer_v2.calculated = calculate_cloud(data=offer_data)
    offer_v2.calculated["cloud_price"] = 0
    for product in ["lightcloud", "heatcloud", "ecloud"]:
        product2 = product
        if product == "lightcloud":
            product2 = "light"
        if data.get(product) not in [None, ""]:
            offer_data[f"{product}_cloud_price_overwrite"] = data.get(product).get("cloud_price_overwrite")
            if data.get(product).get("cloud_price_overwrite"):
                offer_v2.calculated[f"cloud_price_{product2}"] = float(data[product].get("cloud_price"))
                offer_v2.calculated[f"cloud_price_{product2}_incl_refund"] = float(data[product].get("cloud_price")) + offer_v2.calculated[f"cloud_price_extra_{product2}"]
            offer_data[f"{product}_extra_price_per_kwh_overwrite"] = data.get(product).get("extra_price_per_kwh_overwrite")
            if data.get(product).get("extra_price_per_kwh_overwrite"):
                offer_v2.calculated[f"{product}_extra_price_per_kwh"] = float(data[product].get("extra_price_per_kwh"))

        offer_v2.calculated["cloud_price"] = offer_v2.calculated["cloud_price"] + offer_v2.calculated[f"cloud_price_{product2}"]
    offer_data["consumer_cloud_price_overwrite"] = data.get("consumer_cloud_price_overwrite")
    if data.get("consumer_cloud_price_overwrite"):
        offer_v2.calculated["cloud_price_consumer"] = float(data.get("consumer_cloud_price"))
    offer_data["consumer_extra_price_per_kwh_overwrite"] = data.get("consumer_extra_price_per_kwh_overwrite")
    if data.get("consumer_extra_price_per_kwh_overwrite"):
        offer_v2.calculated["consumercloud_extra_price_per_kwh"] = float(data.get("consumercloud_extra_price_per_kwh"))


    offer_v2.calculated["cloud_price_consumer_incl_refund"] = offer_v2.calculated["cloud_price_consumer"]
    offer_v2.calculated["cloud_price"] = offer_v2.calculated["cloud_price"] + offer_v2.calculated["cloud_price_consumer"]
    offer_v2.calculated["cloud_price_incl_refund"] = offer_v2.calculated["cloud_price"] + offer_v2.calculated["cloud_price_extra"]
    items = get_cloud_products(data={"calculated": offer_v2.calculated, "data": offer_data})
    offer_v2.items = []
    for item_data in items:
        item_object = OfferV2Item()
        item_object = set_attr_by_dict(item_object, item_data, ["id"])
        offer_v2.items.append(item_object)

    offer_v2.data = offer_data
    db.session.commit()
    return True


def calculate_year_diff(start_date, end_date, corrected=False):
    start_date = normalize_date(start_date)
    end_date = normalize_date(end_date)
    if corrected in [True, 1, "true"]:
        months = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month
        end_month = monthrange(end_date.year, end_date.month)
        start_month = monthrange(start_date.year, start_date.month)
        if end_date.year == start_date.year and end_date.month == start_date.month:
            percent = (months + (end_date.day - start_date.day + 1) / end_month[1]) / 12
            # print("some-month", start_date, end_date, corrected, percent)
            return percent
        else:
            percent = (months - 1 + (start_month[1] - (start_date.day - 1)) / start_month[1] + end_date.day / end_month[1]) / 12
            # print("different-months1", start_date, end_date, corrected, percent)
            # print("different-months2", months, start_month[1], start_date.day, end_month[1], end_date.day)
            return percent
    percent = (end_date - start_date).days / 365
    # print("days", start_date, end_date, corrected, percent)
    return percent

def string_stripper(text):
    if text is None:
        return None
    return text.strip()


def move_2022_contracts():
    deals = get_deals({
        "SELECT": "full",
        "filter[CATEGORY_ID]": 126,
        "filter[STAGE_ID]": "C126:WON"
    }, force_reload=True)
    deals = deals + get_deals({
        "SELECT": "full",
        "filter[CATEGORY_ID]": 126,
        "filter[STAGE_ID]": "C126:FINAL_INVOICE"
    }, force_reload=True)
    for deal in deals:
        contract = get_contract_data(deal.get("contract_number"), force_reload=False)
        if contract.get("main_deal") is None:
            print(deal.get("contract_number"), "no main deal")
        elif contract.get("cancel_date") not in [None, ""] and normalize_date(contract["cancel_date"]).year <= 2021:
            print(deal.get("contract_number"), contract["cancel_date"])
        elif contract.get("configs") is None or len(contract.get("configs")) == 0:
            print(deal.get("contract_number"), "no configs")
        else:
            last_config = contract.get("configs")[len(contract.get("configs")) - 1]
            if deal.get("cloud_number") != last_config["cloud_number"]:
                update_deal(deal.get("id"), {
                    "stage_id": "C126:UC_XM96DH",
                    "cloud_number": last_config["cloud_number"]
                })
            else:
                update_deal(deal.get("id"), {
                    "stage_id": "C126:UC_XM96DH"
                })


def remove_double_follow_contracts():
    deleted_ids = []
    deleted_contracts = []
    deals = get_deals({
        "SELECT": "full",
        "filter[CATEGORY_ID]": 220,
        "filter[STAGE_ID]": "C220:NEW"
    }, force_reload=True)
    for deal in deals:
        print(".", end = '')
        if deal.get("id") in deleted_ids:
            continue
        if deal.get("cloud_contract_number") in deleted_contracts:
            continue
        for deal2 in deals:
            if deal.get("cloud_contract_number") != deal2.get("cloud_contract_number"):
                continue
            if deal.get("id") == deal2.get("id"):
                continue
            print("")
            print("double", deal.get("cloud_contract_number"))
            deleted_contracts.append(deal.get("cloud_contract_number"))
            deleted_ids.append(deal.get("id"))
            deleted_ids.append(deal2.get("id"))
            print(normalize_date(deal.get("date_create")), normalize_date(deal2.get("date_create")))
            if normalize_date(deal.get("date_create")) < normalize_date(deal2.get("date_create")):
                print("delete", deal2.get("id"))
                delete_deal(deal2.get("id"))
            else:
                print("delete", deal.get("id"))
                delete_deal(deal.get("id"))


def add_cloud_values():
    system_config = get_settings(section="external/bitrix24")
    deals = get_deals({
        "SELECT": "full",
        f"filter[={system_config['deal']['fields']['is_cloud_master_deal']}]": "1",
        "filter[CATEGORY_ID]": 176
    }, force_reload=True)
    for deal in deals:
        print(deal.get("id"))
        if deal.get("price_per_kwh") not in [None, "", 0]:
            continue
        last_config = deal.get("cloud_number")
        for i in range(1, 3):
            if deal.get(f"cloud_number_{i}") not in [None, "", 0]:
                last_config = deal.get(f"cloud_number_{i}")
        if last_config in [None, "", 0, "X"]:
            continue
        try:
            offer_id = int("".join(last_config.split("-")[-1:]))
        except Exception as e:
            print(e)
            continue
        offer_v2 = OfferV2.query.filter(OfferV2.id == offer_id).first()
        if offer_v2 is None or offer_v2.calculated is None or offer_v2.data is None:
            continue
        price_per_kwh = offer_v2.calculated.get("lightcloud_extra_price_per_kwh")
        if price_per_kwh not in [None, "", 0]:
            price_per_kwh = float(price_per_kwh) * 100
        power_extra_usage = offer_v2.data.get("power_extra_usage")
        if power_extra_usage not in [None, "", 0]:
            power_extra_usage = int(power_extra_usage)
        update_data = {
            "price_per_kwh": price_per_kwh,
            "power_extra_usage": power_extra_usage
        }
        update_deal(deal.get("id"), update_data)
        print(json.dumps(update_data, indent=2))
        time.sleep(2)
