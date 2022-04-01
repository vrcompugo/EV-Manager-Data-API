import datetime
from turtle import update
import pytz
import re
import json
import calendar
import math
from dateutil.parser import parse

from app import db
from app.utils.model_func import to_dict
from app.modules.settings import get_settings
from app.modules.external.bitrix24.deal import get_deals, get_deal, update_deal
from app.modules.external.bitrix24.contact import get_contact
from app.modules.external.fakturia.deal import get_payments
from app.modules.external.smartme2.powermeter_measurement import get_device_by_datetime
from app.modules.external.smartme.powermeter_measurement import get_device_by_datetime as get_device_by_datetime2
from app.modules.external.bitrix24.drive import add_file, get_public_link, get_folder_id, create_folder_path
from app.models import SherpaInvoice, ContractStatus, OfferV2, Contract, SherpaInvoiceItem
from .annual_statement import generate_annual_statement_pdf


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


def get_contract_data(contract_number):
    contract_number = normalize_contract_number(contract_number)
    contract2 = Contract.query.filter(Contract.contract_number == contract_number).first()
    config = get_settings(section="external/bitrix24")
    data = {
        "contract_number": contract_number,
        "pv_system": {
            "smartme_number": None,
            "pv_kwp": None,
            "malo_id": None,
            "usages": []
        },
        "cloud": {},
        "deals": [],
        "lightcloud": None,
        "heatcloud": None,
        "ecloud": None,
        "consumers": [],
        "emove": None
    }
    deals = get_deals({
        "SELECT": "full",
        f"FILTER[{config['deal']['fields']['cloud_contract_number']}]": contract_number,
        "FILTER[CATEGORY_ID]": 15
    })
    deals2 = get_deals({
            "SELECT": "full",
            f"FILTER[{config['deal']['fields']['cloud_contract_number']}]": contract_number,
            "FILTER[CATEGORY_ID]": 176
        })
    deals = deals + deals2
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
                "start_value": math.abs(beginning_of_year.get("CounterReading", 0)),
                "end_date": end_of_year.get("Date"),
                "end_value": math.abs(end_of_year.get("CounterReading", 0))
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
                    "start_value": beginning_of_year.get("CounterReading", 0),
                    "end_date": end_of_year.get("Date"),
                    "end_value": end_of_year.get("CounterReading", 0)
                }
                values["usage"] = values["end_value"] - values["start_value"]
                data["pv_system"]["heatcloud_usages"].append(values)
    data["payments"] = get_payments(contract_number)
    return data


def get_annual_statement_data(data, year):
    year = int(year)
    statement = {
        "year": year,
        "counters": [],
        "pv_system": {
            "begin": None,
            "end": None,
            "total_usage": 0,
            "cloud_usage": 0
        }
    }
    status = ContractStatus.query\
        .filter(ContractStatus.contract_number == data.get("contract_number"))\
        .filter(ContractStatus.year == str(year))\
        .first()
    pv_usage = next((item for item in data["pv_system"]["usages"] if item["year"] == year), None)
    sherpaInvoice = SherpaInvoice.query\
        .filter(SherpaInvoice.identnummer == data.get("contract_number"))\
        .filter(SherpaInvoice.abrechnungszeitraum_von >= f"{year}-01-01") \
        .filter(SherpaInvoice.abrechnungszeitraum_von <= f"{year}-12-31") \
        .first()
    cloud_usage = 0
    if sherpaInvoice is not None:
        sherpa_items = SherpaInvoiceItem.query.filter(SherpaInvoiceItem.sherpa_invoice_id == sherpaInvoice.id).all()
        for item in sherpa_items:
            statement["counters"].append(to_dict(item))
        cloud_usage = sherpaInvoice.verbrauch
    else:
        statement["pv_system"]["no_sherpa"] = True
    statement["pv_system"]["cloud_usage"] = cloud_usage
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
    config = get_settings(section="external/bitrix24")

    data = get_contract_data(contract_number)
    if "annualStatements" not in data:
        data["annualStatements"] = []

    statement = get_annual_statement_data(data, year)
    pdf = generate_annual_statement_pdf(data, statement)
    subfolder_id = create_folder_path(415280, path=f"Cloud/Kunde {data['contact_id']}/Vertrag {data['contract_number']}")  # https://keso.bitrix24.de/docs/path/Kundenordner/

    statement["drive_id"] = add_file(folder_id=subfolder_id, data={
        "file_content": pdf,
        "filename": f"Cloud Abrechnung {year}.pdf"
    })
    statement["pdf_link"] = get_public_link(statement["drive_id"])

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

    data["annualStatements"].append(statement)
    return data
