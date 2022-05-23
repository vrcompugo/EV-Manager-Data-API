import datetime
from tkinter import N
from turtle import update
import pytz
import re
import json
import calendar
import math
from dateutil.parser import parse

from app import db
from app.modules.cloud.models.counter_value import CounterValue
from app.utils.model_func import to_dict
from app.modules.settings import get_settings
from app.modules.external.bitrix24.deal import get_deals, get_deal, update_deal
from app.modules.external.bitrix24.contact import get_contact
from app.modules.external.fakturia.deal import get_payments, get_payments2, get_contract
from app.modules.external.smartme2.powermeter_measurement import get_device_by_datetime
from app.modules.external.smartme.powermeter_measurement import get_device_by_datetime as get_device_by_datetime2
from app.modules.external.bitrix24.drive import add_file, get_public_link, get_folder_id, create_folder_path
from app.models import SherpaInvoice, ContractStatus, OfferV2, Contract, SherpaInvoiceItem, Survey
from .annual_statement import generate_annual_statement_pdf


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
        f"FILTER[{system_config['deal']['fields']['cloud_contract_number']}]": contract_number,
        f"FILTER[{system_config['deal']['fields']['is_cloud_master_deal']}]": "1",
        "FILTER[CATEGORY_ID]": 15
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
            f"FILTER[{system_config['deal']['fields']['cloud_contract_number']}]": contract_number,
            "FILTER[CATEGORY_ID]": 176
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
    data["pv_system"]["malo_id"] = data["main_deal"].get("malo_id")
    data["pv_system"]["netprovider"] = data["main_deal"].get("netprovider")
    data["pv_system"]["street"] = data["main_deal"].get("cloud_street")
    data["pv_system"]["street_nb"] = data["main_deal"].get("cloud_street_nb")
    data["pv_system"]["city"] = data["main_deal"].get("cloud_city")
    data["pv_system"]["zip"] = data["main_deal"].get("cloud_zip")
    if data["main_deal"].get("cloud_delivery_begin") not in empty_values and data["main_deal"].get("cloud_number") not in empty_values:
        data = get_cloud_config(data, data["main_deal"].get("cloud_number"), data["main_deal"].get("cloud_delivery_begin"), data["main_deal"].get("cloud_delivery_begin_1"))
    if data["main_deal"].get("cloud_delivery_begin_1") not in empty_values and data["main_deal"].get("cloud_number_1") not in empty_values:
        data = get_cloud_config(data, data["main_deal"].get("cloud_number_1"), data["main_deal"].get("cloud_delivery_begin_1"), data["main_deal"].get("cloud_delivery_begin_2"))
    if data["main_deal"].get("cloud_delivery_begin_2") not in empty_values and data["main_deal"].get("cloud_number_2") not in empty_values:
        data = get_cloud_config(data, data["main_deal"].get("cloud_number_2"), data["main_deal"].get("cloud_delivery_begin_2"), data["main_deal"].get("cloud_delivery_begin_3"))
    if data["main_deal"].get("cloud_delivery_begin_3") not in empty_values and data["main_deal"].get("cloud_number_3") not in empty_values:
        data = get_cloud_config(data, data["main_deal"].get("cloud_number_3"), data["main_deal"].get("cloud_delivery_begin_3"))

    min_delivery_begin = None
    for config in data["configs"]:
        if config["delivery_begin"] not in [None, ""] and (min_delivery_begin is None or min_delivery_begin < parse(config["delivery_begin"])):
            min_delivery_begin = parse(config["delivery_begin"])
    if min_delivery_begin is not None:
        for year in range(min_delivery_begin.year, datetime.datetime.now().year):
            annual_statement = {
                "year": year,
                "status": [],
                "deal": None,
                "data": None,
                "manuell_data": None
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
                annual_statement["data"] = contract_status.data

            deals = get_deals({
                "SELECT": "full",
                f"FILTER[{system_config['deal']['fields']['cloud_contract_number']}]": contract_number,
                "FILTER[CATEGORY_ID]": 126
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
                if deals[0]["stage_id"] == "C126:UC_883FVL":
                    annual_statement["status"].append("old_contract")
                    annual_statement["deal"]["status"] = "Altvertrag manuelle bearbeitung"
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


def get_cloud_config(data, cloud_number, delivery_begin, delivery_end):
    settings = get_settings(section="external/bitrix24")
    config = {
        "cloud_number": cloud_number,
        "delivery_begin": delivery_begin,
        "delivery_end": None,
        "consumers": [],
        "errors": []
    }
    if delivery_end not in empty_values:
        config["delivery_end"] = delivery_end
    else:
        if data.get("cancel_date") not in empty_values:
            config["delivery_end"] = data.get("cancel_date")
    offer_v2 = OfferV2.query.filter(OfferV2.number == cloud_number).first()
    if offer_v2 is None:
        config["errors"].append({
            "code": "config not found",
            "message": "Angebotsnummer konnte nicht gefunden werden."
        })
    else:
        data["pv_system"]["pv_kwp"] = offer_v2.calculated.get("pv_kwp")
        data["pv_system"]["storage_size"] = offer_v2.calculated.get("storage_size")
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
        if offer_v2.calculated.get("min_kwp_light") > 0:
            config["lightcloud"] = {
                "label": "Lichtcloud",
                "usage": offer_v2.calculated.get("power_usage"),
                "extra_price_per_kwh": offer_v2.calculated.get("lightcloud_extra_price_per_kwh"),
                "cloud_price": offer_v2.calculated.get(f"cloud_price_light"),
                "cloud_price_incl_refund": offer_v2.calculated.get("cloud_price_light_incl_refund"),
                "smartme_number": data["main_deal"].get("smartme_number"),
                "power_meter_number": data["main_deal"].get("delivery_counter_number"),
                "additional_power_meter_numbers": [],
                "delivery_begin": data["main_deal"].get("cloud_delivery_begin"),
                "deal": {
                    "id": data["main_deal"].get("id"),
                    "title": data["main_deal"].get("title")
                }
            }
            if config["lightcloud"]["smartme_number"] not in empty_values:
                config["lightcloud"]["smartme_number"] = config["lightcloud"]["smartme_number"].strip()
            if config["lightcloud"]["power_meter_number"] not in empty_values:
                config["lightcloud"]["power_meter_number"] = config["lightcloud"]["power_meter_number"].strip()
            if data["main_deal"].get("delivery_counter_number2") not in empty_values:
                config["lightcloud"]["additional_power_meter_numbers"].append(data["main_deal"].get("delivery_counter_number2"))
            if data["main_deal"].get("delivery_counter_number3") not in empty_values:
                config["lightcloud"]["additional_power_meter_numbers"].append(data["main_deal"].get("delivery_counter_number3"))
            if data["main_deal"].get("old_power_meter_numbers") not in empty_values:
                numbers = data["main_deal"].get("old_power_meter_numbers").split("\n")
                for number in numbers:
                    number = number.strip()
                    if number != "" and number not in config["lightcloud"]["additional_power_meter_numbers"]:
                        config["lightcloud"]["additional_power_meter_numbers"].append(number)
        if offer_v2.calculated.get("min_kwp_emove") > 0:
            config["emove"] = {
                "label": "eMove",
                "tarif": offer_v2.data.get("emove_tarif"),
                "cloud_price": offer_v2.calculated.get(f"cloud_price_emove"),
                "cloud_price_incl_refund": offer_v2.calculated.get("cloud_price_emove_incl_refund"),
                "extra_price_per_kwh": offer_v2.calculated.get("lightcloud_extra_price_per_kwh"),
                "usage": float(data["main_deal"].get("emove_usage_inhouse")),
                "usage_outside": float(data["main_deal"].get("emove_usage_outside")),
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
                "cloud_price": offer_v2.calculated.get(f"cloud_price_heatcloud"),
                "cloud_price_incl_refund": offer_v2.calculated.get("cloud_price_heatcloud_incl_refund"),
                "extra_price_per_kwh": offer_v2.calculated.get("heatcloud_extra_price_per_kwh"),
                "additional_power_meter_numbers": [],
                "deal": None
            }
            deals = get_deals({
                "SELECT": "full",
                f"FILTER[{settings['deal']['fields']['cloud_contract_number']}]": data["contract_number"],
                f"FILTER[{settings['deal']['fields']['is_cloud_heatcloud']}]": "1",
                "FILTER[CATEGORY_ID]": 15
            }, force_reload=True)
            if len(deals) != 1:
                config["errors"].append({
                    "code": "deal_not_found",
                    "message": "Wärmecloud Auftrag nicht gefunden"
                })
            else:
                config["heatcloud"]["smartme_number"] = deals[0].get("smartme_number_heatcloud")
                config["heatcloud"]["power_meter_number"] = deals[0].get("heatcloud_power_meter_number")
                config["heatcloud"]["delivery_begin"] = deals[0].get("cloud_delivery_begin")
                config["heatcloud"]["deal"] = {
                    "id": deals[0].get("id"),
                    "title": deals[0].get("title")
                }
                if config["heatcloud"]["power_meter_number"] not in empty_values:
                    config["heatcloud"]["power_meter_number"] = config["heatcloud"]["power_meter_number"].strip()
                if deals[0].get("old_power_meter_numbers") not in empty_values:
                    numbers =  deals[0].get("old_power_meter_numbers").split("\n")
                    for number in numbers:
                        number = number.strip()
                        if number != "" and number not in config["heatcloud"]["additional_power_meter_numbers"]:
                            config["heatcloud"]["additional_power_meter_numbers"].append(number)
        if offer_v2.calculated.get("min_kwp_ecloud") > 0:
            config["ecloud"] = {
                "label": "eCloud",
                "usage": offer_v2.calculated.get("ecloud_usage"),
                "power_meter_number": None,
                "additional_power_meter_numbers": [],
                "cloud_price": offer_v2.calculated.get(f"cloud_price_ecloud"),
                "cloud_price_incl_refund": offer_v2.calculated.get("cloud_price_ecloud_incl_refund"),
                "extra_price_per_kwh": offer_v2.calculated.get("ecloud_extra_price_per_kwh"),
                "deal": None
            }
            deals = get_deals({
                "SELECT": "full",
                f"FILTER[{settings['deal']['fields']['cloud_contract_number']}]": data["contract_number"],
                f"FILTER[{settings['deal']['fields']['is_cloud_ecloud']}]": "1",
                "FILTER[CATEGORY_ID]": 15
            }, force_reload=True)
            if len(deals) != 1:
                config["errors"].append({
                    "code": "deal_not_found",
                    "message": "eCloud Auftrag nicht gefunden"
                })
            else:
                config["ecloud"]["smartme_number"] = None
                config["ecloud"]["power_meter_number"] = deals[0].get("counter_ecloud")
                config["ecloud"]["delivery_begin"] = deals[0].get("cloud_delivery_begin")
                config["ecloud"]["deal"] = {
                    "id": deals[0].get("id"),
                    "title": deals[0].get("title")
                }
                if config["ecloud"]["power_meter_number"] not in empty_values:
                    config["ecloud"]["power_meter_number"] = config["ecloud"]["power_meter_number"].strip()
                if  deals[0].get("old_power_meter_numbers") not in empty_values:
                    numbers =  deals[0].get("old_power_meter_numbers").split("\n")
                    for number in numbers:
                        number = number.strip()
                        if number != "" and number not in config["ecloud"]["additional_power_meter_numbers"]:
                            config["ecloud"]["additional_power_meter_numbers"].append(number)
        if offer_v2.calculated.get("min_kwp_consumer") > 0:
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
                f"FILTER[{settings['deal']['fields']['cloud_contract_number']}]": data["contract_number"],
                f"FILTER[{settings['deal']['fields']['is_cloud_consumer']}]": "1",
                "FILTER[CATEGORY_ID]": 15
            }, force_reload=True)
            for index, consumer in enumerate(config["consumers"]):
                existing_deal = next((i for i in deals if str(i["delivery_usage"]) == str(consumer["usage"])), None)
                if existing_deal is None:
                    config["errors"].append({
                        "code": "deal_not_found",
                        "message": f"Consumer {index + 1} Auftrag nicht gefunden"
                    })
                else:
                    consumer["power_meter_number"] = existing_deal.get("delivery_counter_number")
                    consumer["delivery_begin"] = existing_deal.get("cloud_delivery_begin")
                    if  existing_deal.get("old_power_meter_numbers") not in empty_values:
                        numbers =  existing_deal.get("old_power_meter_numbers").split("\n")
                        for number in numbers:
                            number = number.strip()
                            if number != "" and number not in consumer["additional_power_meter_numbers"]:
                                consumer["additional_power_meter_numbers"].append(number)
                    consumer["deal"] = {
                        "id": existing_deal.get("id"),
                        "title": existing_deal.get("title")
                    }
            config["consumer_data"] = {
                "cloud_price": offer_v2.calculated.get(f"cloud_price_consumer"),
                "cloud_price_incl_refund": offer_v2.calculated.get("cloud_price_consumer_incl_refund"),
                "extra_price_per_kwh": offer_v2.calculated.get("consumercloud_extra_price_per_kwh"),
            }

    data["configs"].append(config)
    return data


def get_annual_statement_data(data, year, manuell_data):
    year = int(year)
    if manuell_data is None:
        manuell_data = {}
    statement = {
        "year": year,
        "contact": get_contact(data.get("contact_id")),
        "counters": [],
        "configs": [],
        "errors": [],
        "warnings": [],
        "pv_system": data["pv_system"],
        "total_usage": 0,
        "total_extra_usage": 0,
        "total_extra_price": 0,
        "total_extra_price_net": 0,
        "total_cloud_price": 0,
        "total_cloud_price_incl_refund": 0,
        "available_values": []
    }
    counter_numbers = []
    sherpa_counters = []
    sherpaInvoices = SherpaInvoice.query\
        .filter(SherpaInvoice.identnummer == data.get("contract_number"))\
        .filter(SherpaInvoice.abrechnungszeitraum_von >= f"{year}-01-01") \
        .filter(SherpaInvoice.abrechnungszeitraum_von <= f"{year}-12-31") \
        .all()
    for sherpaInvoice in sherpaInvoices:
        sherpa_items = SherpaInvoiceItem.query.filter(SherpaInvoiceItem.sherpa_invoice_id == sherpaInvoice.id).all()
        for item in sherpa_items:
            existing_counter = next((i for i in sherpa_counters if i["number"] == item.zahlernummer and i["start_date"] == str(item.datum_stand_alt) and i["end_date"] == str(item.datum_stand_neu)), None)
            if existing_counter is not None:
                existing_counter["start_value"] = existing_counter["start_value"] + item.stand_alt
                existing_counter["end_value"] = existing_counter["end_value"] + item.stand_neu
                existing_counter["usage"] = existing_counter["usage"] + item.verbrauch
            else:
                sherpa_counters.append({
                    "number": item.zahlernummer,
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

        if manuell_data.get("cashback_price_per_kwh") not in [None, ""]:
            statement_config["cashback_price_per_kwh"] = float(manuell_data.get("cashback_price_per_kwh")) / 100
        if manuell_data.get("ecloud_cashback_price_per_kwh") not in [None, ""]:
            statement_config["ecloud_cashback_price_per_kwh"] = float(manuell_data.get("ecloud_cashback_price_per_kwh")) / 100
        statement_config["total_usage"] = 0
        statement_config["total_extra_usage"] = 0
        statement_config["total_extra_price"] = 0
        statement_config["total_cloud_price"] = 0
        statement_config["total_cloud_price_incl_refund"] = 0
        delivery_end = str(parse(config.get("delivery_begin")).year) + "-12-31"
        if config.get("delivery_end") is not None:
            delivery_end = str(config.get("delivery_end"))
        delivery_begin = str(parse(config.get("delivery_begin")).year) + "-01-01"
        if parse(config.get("delivery_begin")).year == year:
            delivery_begin = str(config.get("delivery_begin"))
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
                if product == "lightcloud" and statement_config[product]["extra_price_per_kwh"] < 0.3379:
                    statement_config[product]["extra_price_per_kwh"] = 0.3379
                if manuell_data.get(f"{product}_extra_price_per_kwh") not in [None, ""]:
                    statement_config[product]["extra_price_per_kwh"] = float(manuell_data.get(f"{product}_extra_price_per_kwh")) / 100
                product_delivery_begin = f"{year}-01-01"
                if parse(statement_config[product].get("delivery_begin")).year == year:
                    product_delivery_begin = parse(statement_config[product].get("delivery_begin"))
                statement_config[product]["delivery_begin"] = str(product_delivery_begin)
                statement_config[product]["delivery_end"] = str(delivery_end)
                diff_days = (normalize_date(statement_config[product]["delivery_end"]) - normalize_date(statement_config[product]["delivery_begin"])).days
                statement_config[product]["allowed_usage"] = statement_config[product]["usage"] * (diff_days / 365)

                if product == "lightcloud" and config.get("emove") is not None:
                    statement_config[product]["label"] = statement_config[product]["label"] + " inkl. eMove"
                    statement_config[product]["allowed_usage_emove"] = float(statement_config["emove"]["usage"]) * (diff_days / 365)
                    statement_config[product]["allowed_usage"] = statement_config[product]["allowed_usage"] + statement_config[product]["allowed_usage_emove"]
                statement_config[product]["actual_usage"] = 0
                statement_config[product]["actual_usage_net"] = 0
                if statement_config[product].get("power_meter_number") not in [None, "", "123", 0, "0"]:
                    counter_numbers.append(statement_config[product].get("power_meter_number"))
                    values = []
                    for value in statement["available_values"]:
                        if value["number"] == statement_config[product].get("power_meter_number") or value["number"] in statement_config[product].get("additional_power_meter_numbers", []):
                            values.append(value)
                    if product == "lightcloud" and "heatcloud" in statement_config and statement_config["lightcloud"]["delivery_begin"] != statement_config["heatcloud"]["delivery_begin"]:
                        counters = normalize_counter_values(
                            statement_config["lightcloud"]["delivery_begin"],
                            statement_config["heatcloud"]["delivery_begin"],
                            [statement_config[product].get("power_meter_number")] + statement_config[product].get("additional_power_meter_numbers", []),
                            values.copy()
                        )
                        counters2 = normalize_counter_values(
                            statement_config["heatcloud"]["delivery_begin"],
                            statement_config["lightcloud"]["delivery_end"],
                            [statement_config[product].get("power_meter_number")] + statement_config[product].get("additional_power_meter_numbers", []),
                            values.copy(),
                            True
                        )
                        if counters is not None and len(counters) > 0 and counters2 is not None and len(counters2) > 0:
                            statement_config[product]["actual_usage_net"] = sum(item['usage'] for item in counters2)
                            statement_config["heatcloud"]["actual_usage_net"] = statement_config["heatcloud"]["actual_usage_net"] - statement_config[product]["actual_usage_net"]
                            statement_config[product]["actual_usage_net"] = statement_config[product]["actual_usage_net"] + sum(item['usage'] for item in counters)
                            statement["counters"] = statement["counters"] + counters
                            statement["counters"] = statement["counters"] + counters2
                    else:
                        counters = normalize_counter_values(
                            statement_config[product]["delivery_begin"],
                            statement_config[product]["delivery_end"],
                            [statement_config[product].get("power_meter_number")] + statement_config[product].get("additional_power_meter_numbers", []),
                            values
                        )
                        if counters is not None and len(counters) > 0:
                            if product in ["lightcloud", "heatcloud"]:
                                statement_config[product]["actual_usage_net"] = sum(item['usage'] for item in counters)
                            else:
                                statement_config[product]["actual_usage"] = sum(item['usage'] for item in counters)
                            statement["counters"] = statement["counters"] + counters
                if statement_config[product].get("smartme_number") not in [None, "", "123", 0, "0"]:
                    counter_numbers.append(statement_config[product].get("smartme_number"))
                    beginning_of_year = get_device_by_datetime(statement_config[product].get("smartme_number"), statement_config[product]["delivery_begin"])
                    end_of_year = get_device_by_datetime(statement_config[product].get("smartme_number"), statement_config[product]["delivery_end"])
                    if beginning_of_year is not None and end_of_year is not None:
                        values = [
                            {
                                "number": statement_config[product].get("smartme_number"),
                                "date": normalize_date(beginning_of_year.get("Date")),
                                "value": abs(beginning_of_year.get("CounterReading", 0)),
                                "origin": "smartme"
                            },
                            {
                                "number": statement_config[product].get("smartme_number"),
                                "date": normalize_date(end_of_year.get("Date")),
                                "value": abs(end_of_year.get("CounterReading", 0)),
                                "origin": "smartme"
                            }
                        ]
                        statement["available_values"] = statement["available_values"] + values
                        counters = normalize_counter_values(
                            statement_config[product]["delivery_begin"],
                            statement_config[product]["delivery_end"],
                            [statement_config[product].get("smartme_number")],
                            values
                        )
                        if counters is not None and len(counters) > 0:
                            statement_config[product]["actual_usage"] = sum(item['usage'] for item in counters)
                            statement["counters"] = statement["counters"] + counters

                percent_year = (normalize_date(statement_config[product]["delivery_end"]) - normalize_date(statement_config[product]["delivery_begin"])).days / 365
                statement_config[product]["total_cloud_price"] = statement_config[product]["cloud_price"] * 12 * percent_year
                statement_config[product]["total_cloud_price_incl_refund"] = statement_config[product]["cloud_price_incl_refund"] * 12 * percent_year
                statement_config["total_cloud_price"] = statement_config["total_cloud_price"] + statement_config[product]["cloud_price_incl_refund"] * 12 * percent_year
                statement_config["total_cloud_price_incl_refund"] = statement_config["total_cloud_price_incl_refund"] + statement_config[product]["total_cloud_price_incl_refund"]
                statement_config[product]["total_extra_usage"] = statement_config[product]["actual_usage"] - statement_config[product]["allowed_usage"]
                statement_config[product]["total_extra_price"] = 0
                if statement_config[product]["total_extra_usage"] < -250:
                    if product == "ecloud":
                        statement_config[product]["cashback_price_per_kwh"] = statement_config["ecloud_cashback_price_per_kwh"]
                    else:
                        statement_config[product]["cashback_price_per_kwh"] = statement_config["cashback_price_per_kwh"]
                    statement_config[product]["total_extra_price"] = (statement_config[product]["total_extra_usage"] + 250) * statement_config[product]["cashback_price_per_kwh"]

                elif statement_config[product]["total_extra_usage"] > 0:
                    statement_config[product]["total_extra_price"] = statement_config[product]["total_extra_usage"] * statement_config[product]["extra_price_per_kwh"]
                statement_config["total_extra_price"] = statement_config["total_extra_price"] + statement_config[product]["total_extra_price"]
                statement_config["total_extra_usage"] = statement_config["total_extra_usage"] + statement_config[product]["total_extra_usage"]
                statement_config["total_usage"] = statement_config["total_usage"] + statement_config[product]["actual_usage"]
            statement["total_usage"] = statement["total_usage"] + statement_config["total_usage"]
            statement["total_extra_usage"] = statement["total_extra_usage"] + statement_config["total_extra_usage"]
            statement["total_cloud_price"] = statement["total_cloud_price"] + statement_config["total_cloud_price"]
            statement["total_cloud_price_incl_refund"] = statement["total_cloud_price_incl_refund"] + statement_config["total_cloud_price_incl_refund"]
            statement["total_extra_price"] = statement["total_extra_price"] + statement_config["total_extra_price"]

            statement_config["consumers"] = []
            for customer_product in customer_products:
                statement_config["consumers"].append(statement_config[customer_product])
            for product in ["heatcloud", "lightcloud", "ecloud"] + customer_products:
                if product not in statement_config:
                    continue
                if statement_config[product]["actual_usage"] <= 0:
                    statement["errors"].append(f"{statement_config[product]['label']} hat keinen Verbrauch")
                if statement_config[product]["actual_usage"] < statement_config[product]["actual_usage_net"]:
                    statement["errors"].append(f"{statement_config[product]['label']} Netzbezug ist größer als der Gesamtverbrauch")
                if statement_config[product]["actual_usage"] > 0 and statement_config[product]["actual_usage_net"]/statement_config[product]["actual_usage"] > 0.8 :
                    statement["warnings"].append(f"{statement_config[product]['label']} Netzbezug ist mehr als 80% vom Gesamtverbrauch")
                if product == "lightcloud" and statement_config[product]["actual_usage_net"] <= 0:
                    statement["warnings"].append(f"{statement_config[product]['label']} Netzbezug ist nicht vorhanden")
            statement["configs"].append(statement_config)
    statement["total_extra_price_net"] = statement["total_extra_price"] / 1.19
    statement["total_cloud_price_net"] = statement["total_cloud_price"] / 1.19
    statement["total_cloud_price_incl_refund_net"] = statement["total_cloud_price_incl_refund"] / 1.19

    statement["pre_payments_total"] = statement["total_cloud_price_incl_refund"]
    if data.get("fakturia") is not None and data.get("fakturia").get("contractStatus") not in ["ENDED"]:
        statement["payments"] = []
        statement["pre_payments_total"] = 0
        for payment in data.get("invoices_credit_notes"):
            if payment["date"][:4] == str(year):
                statement["pre_payments_total"] = statement["pre_payments_total"] + payment["amountGross"]
                statement["payments"].append(payment)

    statement["to_pay"] = statement["total_cloud_price_incl_refund"] - statement["pre_payments_total"] + statement["total_extra_price"]
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
            f"FILTER[{config['deal']['fields']['cloud_contract_number']}]": contract_number,
            "FILTER[CATEGORY_ID]": 126,
        })
        if deals is not None and len(deals) > 0:
            deal_id = deals[0].get("id")
            update_deal(deal_id, {
                # "stage_id": "C126:UC_WT48N4",
                "annual_statement_link": statement["pdf_link"],
                "opportunity": statement["to_pay"]
            })
    db.session.commit()
    return data


def normalize_date(datetime):
    return parse(parse(str(datetime)).strftime("%Y-%m-%d"))


def normalize_counter_values(start_date, end_date, numbers, values, debug=False):
    counters = []
    for number in numbers:
        start_date = normalize_date(start_date)
        end_date = normalize_date(end_date)
        start_value_earlier = CounterValue.query.filter(CounterValue.number == number)\
            .filter(CounterValue.date <= start_date)\
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
            if value["number"] == number:
                if value["date"] < start_date:
                    start_value = value
                if value["date"] == start_date:
                    start_value = value
                if value["date"] > start_date:
                    if start_value is None:
                        start_value = value
                    elif (start_date - start_value["date"]).days > (value["date"] - start_date).days:
                        start_value2 = start_value
                        start_value = value
                if value["date"] < end_date:
                    end_value = value
                if value["date"] == end_date:
                    end_value = value
                if value["date"] > end_date:
                    if end_value is None:
                        end_value = value
                    elif (end_date - end_value["date"]).days > (value["date"] - end_date).days:
                        end_value = value
        if start_value == end_value:
            start_value = start_value2
        if end_value is None or start_value is None:
            return None
        origin = start_value["origin"]
        if start_value["origin"] != end_value["origin"]:
            origin = f'{start_value["origin"]}/{end_value["origin"]}'
        counters.append({
            "number": number,
            "type": origin,
            "start_date": start_value["date"],
            "start_value": start_value["value"],
            "start_estimated": False,
            "end_date": end_value["date"],
            "end_value": end_value["value"],
            "end_estimated": False,
        })
        # print(counters)
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

    diff_days_target = (end_date - start_date).days
    diff_days_value = (last_counter["end_date"] - first_counter["start_date"]).days
    if diff_days_target < 100:
        if diff_days_target * 0.2 > diff_days_value:
            return None
    else:
        if diff_days_target * 0.3 > diff_days_value:
            return None

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


def test_normalize_counter_values():
    values = [
        { "date": normalize_date("2020-11-23"), "value": 500, "origin": "smartme"},
        { "date": normalize_date("2021-01-12"), "value": 1500, "origin": "smartme"},
        { "date": normalize_date("2021-09-12"), "value": 2500, "origin": "smartme"},
        { "date": normalize_date("2021-12-12"), "value": 2500, "origin": "smartme"},
        { "date": normalize_date("2022-02-01"), "value": 3500, "origin": "smartme"},
    ]
    print(json.dumps(normalize_counter_values(normalize_date("2021-01-01"), normalize_date("2021-12-31"), "sad", values), indent=2))
    values = [
        { "date": normalize_date("2020-11-23"), "value": 500, "origin": "smartme"}
    ]
    print(json.dumps(normalize_counter_values(normalize_date("2021-01-01"), normalize_date("2021-12-31"), "sad", values), indent=2))
    values = [
        { "date": normalize_date("2022-02-01"), "value": 500, "origin": "smartme"}
    ]
    print(json.dumps(normalize_counter_values(normalize_date("2021-01-01"), normalize_date("2021-12-31"), "sad", values), indent=2))
    values = [
        { "date": normalize_date("2021-04-01"), "value": 500, "origin": "manuell"},
        { "date": normalize_date("2022-02-01"), "value": 2500, "origin": "smartme"}
    ]
    print(json.dumps(normalize_counter_values(normalize_date("2021-01-01"), normalize_date("2021-12-31"), "sad", values), indent=2))
    values = [
        { "date": normalize_date("2021-01-01"), "value": 500, "origin": "manuell"},
        { "date": normalize_date("2023-12-21"), "value": 2500, "origin": "smartme"}
    ]
    print(json.dumps(normalize_counter_values(normalize_date("2021-01-01"), normalize_date("2021-12-31"), "1APADB72207196", values), indent=2))