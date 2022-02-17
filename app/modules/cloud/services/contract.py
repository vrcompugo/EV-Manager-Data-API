import datetime
import pytz
import re
import json
import calendar
from dateutil.parser import parse

from app.modules.settings import get_settings
from app.modules.external.bitrix24.deal import get_deals, get_deal
from app.modules.external.bitrix24.contact import get_contact
from app.modules.external.smartme2.powermeter_measurement import get_device_by_datetime


def get_contract_data(contract_number):
    contract_number = normalize_contract_number(contract_number)
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
        "FILTER[CATEGORY_ID]": 174,
    })
    if len(deals) >= 1:
        print("perfect")
    else:
        deals = get_deals({
            "SELECT": "full",
            f"FILTER[{config['deal']['fields']['cloud_contract_number']}]": contract_number,
            "FILTER[CATEGORY_ID]": 15
        })
    if deals is not None:
        data["deals"] = deals
        for deal in deals:
            if deal.get("is_cloud_master_deal") in [True, "1", 1]:
                print(json.dumps(deal, indent=2))
                data["contact_id"] = deal.get("contact_id")
                data["pv_system"]["smartme_number"] = deal.get("smartme_number")
                data["pv_system"]["pv_kwp"] = deal.get("pv_kwp")
                data["pv_system"]["malo_id"] = deal.get("malo_id")
                data["pv_system"]["power_meter_number"] = deal.get("power_meter_number")
                data["pv_system"]["street"] = deal.get("cloud_street")
                data["pv_system"]["street_nb"] = deal.get("cloud_street_nb")
                data["pv_system"]["city"] = deal.get("cloud_city")
                data["pv_system"]["zip"] = deal.get("cloud_zip")
                data["pv_system"]["netprovider"] = deal.get("netprovider")
                data["cloud"]["cloud_monthly_price"] = deal.get("cloud_monthly_price")
                data["cloud"]["extra_price_per_kwh"] = deal.get("extra_price_per_kwh")
                data["cloud"]["cashback_per_kwh"] = deal.get("cashback_per_kwh")
                data["lightcloud"] = {
                    "status": get_item_status(deal),
                    "usage": deal.get("lightcloud_usage"),
                    "delivery_begin": deal.get("cloud_delivery_begin"),
                    "cancelation_date": deal.get("cancelation_date"),
                    "cancelation_due_date": deal.get("cancelation_due_date")
                }
                if deal.get("emove_packet") not in [None, "0", 0, ""]:
                    data["emove"] = {
                        "status": get_item_status(deal),
                        "packet": deal.get("emove_packet"),
                        "usage_inhouse": deal.get("emove_usage_inhouse"),
                        "usage_outside": deal.get("emove_usage_inhouse"),
                        "delivery_begin": deal.get("cloud_delivery_begin"),
                        "cancelation_date": deal.get("cancelation_date"),
                        "cancelation_due_date": deal.get("cancelation_due_date")
                    }
            if deal.get("is_cloud_heatcloud") in [True, "1", 1]:
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
    if data["pv_system"].get("smartme_number") not in [None, "", "0", 0]:
        delivery_begin = parse(data["lightcloud"].get("delivery_begin"))
        start_year = delivery_begin.year
        end_year = datetime.datetime.now().year
        for year in range(start_year, end_year + 1):
            if delivery_begin.year == year:
                beginning_of_year = get_device_by_datetime(data["pv_system"].get("smartme_number"), data["lightcloud"].get("delivery_begin"))
            else:
                beginning_of_year = get_device_by_datetime(data["pv_system"].get("smartme_number"), f"{year}-01-01 00:00:00")
            end_of_year = get_device_by_datetime(data["pv_system"].get("smartme_number"), f"{year}-12-31 23:59:59")
            values = {
                "year": year,
                "start_date": beginning_of_year.get("Date"),
                "start_value": beginning_of_year.get("CounterReading", 0),
                "end_date": end_of_year.get("Date"),
                "end_value": end_of_year.get("CounterReading", 0)
            }
            values["usage"] = values["end_value"] - values["start_value"]
            data["pv_system"]["usages"].append(values)
    return data


def get_annual_statement_data(data, year):
    year = int(year)
    lightcloud_begin = parse(data["lightcloud"]["delivery_begin"])
    if lightcloud_begin.year < year:
        lightcloud_begin = parse(f"{year}-01-01")
    lightcloud_end = parse(f"{year}-12-31")
    if data["lightcloud"].get("cancelation_due_date") not in ["", None, 0, "0"]:
        enddate = parse(data["lightcloud"]["cancelation_due_date"])
        if enddate.year == year:
            lightcloud_end = enddate
    pv_usage = next((item for item in data["pv_system"]["usages"] if item["year"] == year), None)
    statement = {
        "year": year,
        "pv_system": {
            "begin": pv_usage["start_date"],
            "end": pv_usage["end_date"],
            "total_usage": int(pv_usage["usage"]),
            "cloud_usage": 917
        }
    }
    statement["pv_system"]["direct_usage"] = statement["pv_system"]["total_usage"] - statement["pv_system"]["cloud_usage"]
    statement["lightcloud"] = {
        "begin": lightcloud_begin,
        "end": lightcloud_end,
        "year_percent": (diff_month(lightcloud_end, lightcloud_begin) / 12),
        "extra_price_per_kwh": 0.2769 ,
        "cashback_per_kwh": 0.10,
        "price_per_month": -2.25
    }
    statement["lightcloud"]["included_usage"] = int(int(data["lightcloud"]["usage"]) * statement["lightcloud"]["year_percent"])
    statement["lightcloud"]["price"] = statement["lightcloud"]["price_per_month"] * 12 * statement["lightcloud"]["year_percent"]
    statement["total_extra_usage"] = statement["pv_system"]["total_usage"] - statement["lightcloud"]["included_usage"]
    statement["total_extra_usage_price"] = statement["total_extra_usage"] * statement["lightcloud"]["extra_price_per_kwh"]
    statement["pre_payments"] = []
    statement["pre_payments"].append({
        "label": "Vorauszahlungen",
        "begin": lightcloud_begin,
        "end": lightcloud_end,
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
    months = (d1.year - d2.year) * 12 + d1.month - d2.month
    _null, last_day = calendar.monthrange(d1.year, d1.month)
    months = months + (1 - (d1.day - 1) / (last_day - 1))
    _null, last_day = calendar.monthrange(d2.year, d2.month)
    months = months + (1 - (d2.day - 1) / (last_day - 1))
    return months