
import pdfkit
import json
import subprocess
import tempfile
from flask import render_template, request, make_response
from PyPDF2 import PdfFileWriter, PdfFileReader
from io import StringIO, BytesIO
import dateutil

from app.modules.settings.settings_services import get_one_item as get_settings
from app.modules.file.file_services import add_item as add_file, update_item as update_file
from app.models import OfferV2, S3File, EEGRefundRate
from app.utils.gotenberg import generate_pdf as gotenberg_pdf
from app.modules.cloud.services.calculation import cloud_offer_calculation_by_pv_offer

from ..offer_generation.cloud_offer import cloud_offer_items_by_pv_offer


def calculate_feasibility_study(offer: OfferV2):
    settings = get_settings("pv-settings")
    if settings is None:
        return None
    pv_efficiancy = None
    settings["data"]["wi_settings"]["pv_efficiancy"] = {
        "south": 915,
        "west_east": 825,
        "north_west_east": 620,
        "south_west_east": 850,
        "north": 560
    }
    if offer is not None and offer.reseller is not None and offer.reseller.document_style == "bsh":
        settings["data"]["wi_settings"]["pv_efficiancy"] = {
            "south": 1000,
            "west": 860,
            "east": 860,
            "west_east": 860,
            "south_west": 920,
            "south_east": 920,
            "south_west_east": 920,
            "north": 750,
            "north_west": 800,
            "north_east": 800
        }
        if "pv_efficiancy" in offer.data and offer.data["pv_efficiancy"] is not None and offer.data["pv_efficiancy"] != "":
            pv_efficiancy = int(1150 * int(offer.data["pv_efficiancy"]) / 1150)
    in_use_date = offer.datetime + dateutil.relativedelta.relativedelta(months=1)
    price_increase_heat = 2
    price_increase_ecloud = 2
    price_increase_emove = 2.5
    investment_type = "financing"
    loan_interest_rate = None
    pv_offer_total = float(offer.total - offer.total_tax)
    if offer.offer_group == "cloud-offer":
        cloud_runtime = 2
        if offer.data["price_guarantee"] == "10_years":
            cloud_runtime = 10
        if offer.data["price_guarantee"] == "12_years":
            cloud_runtime = 12
        cloud_calulation = offer.calculated
        consumer = 1
        usage = offer.calculated["power_usage"]
        heatcloud_usage = offer.calculated["heater_usage"]
        ecloud_usage = offer.calculated["ecloud_usage"]
        run_time = 30
        if "runtime" in offer.data and offer.data["runtime"] is not None and offer.data["runtime"] != "":
            run_time = int(offer.data["runtime"])
        price_increase = 5.75
        if offer.reseller is not None and offer.reseller.document_style == "bsh":
            price_increase = 3.5
        inflation_rate = 2.5
        if "price_increase_rate" in offer.data and offer.data["price_increase_rate"] != "":
            price_increase = float(offer.data["price_increase_rate"])
            if offer.reseller is not None and offer.reseller.document_style == "bsh":
                price_increase_heat = float(offer.data["price_increase_rate"])
        if "inflation_rate" in offer.data and offer.data["inflation_rate"] != "":
            inflation_rate = float(offer.data["inflation_rate"])
        if "investment_type" in offer.data and offer.data["investment_type"] != "":
            investment_type = offer.data["investment_type"]
        if "financing_rate" in offer.data and offer.data["financing_rate"] != "":
            loan_interest_rate = float(offer.data["financing_rate"])
        packet = 50
        if pv_efficiancy is None:
            pv_efficiancy = settings["data"]["wi_settings"]["pv_efficiancy"]["west_east"]
            if "roof_direction" in offer.data and offer.data["roof_direction"] == "north":
                pv_efficiancy = settings["data"]["wi_settings"]["pv_efficiancy"][offer.data["roof_direction"]]
            if "roof_direction" in offer.data and offer.data["roof_direction"] == "south":
                pv_efficiancy = settings["data"]["wi_settings"]["pv_efficiancy"][offer.data["roof_direction"]]
            if "roof_direction" in offer.data and offer.data["roof_direction"] == "south_west_east":
                pv_efficiancy = settings["data"]["wi_settings"]["pv_efficiancy"][offer.data["roof_direction"]]
        orientation = offer.data["roof_direction"]
        orientation_label = "West/Ost"
        if "roof_direction" in offer.data and offer.data["roof_direction"] == "north":
            orientation_label = "Nord"
        if "roof_direction" in offer.data and offer.data["roof_direction"] == "north_west":
            orientation_label = "Nord West"
        if "roof_direction" in offer.data and offer.data["roof_direction"] == "north_east":
            orientation_label = "Nord Ost"
        if "roof_direction" in offer.data and offer.data["roof_direction"] == "north_west_east":
            orientation_label = "Nord West/Nord Ost"
        if "roof_direction" in offer.data and offer.data["roof_direction"] == "north_south":
            orientation_label = "Nord/Süd"
        if "roof_direction" in offer.data and offer.data["roof_direction"] == "west_east":
            orientation_label = "West/Ost"
        if "roof_direction" in offer.data and offer.data["roof_direction"] == "west":
            orientation_label = "West"
        if "roof_direction" in offer.data and offer.data["roof_direction"] == "east":
            orientation_label = "Ost"
        if "roof_direction" in offer.data and offer.data["roof_direction"] == "south_west":
            orientation_label = "Süd West"
        if "roof_direction" in offer.data and offer.data["roof_direction"] == "south_east":
            orientation_label = "Süd Ost"
        if "roof_direction" in offer.data and offer.data["roof_direction"] == "south_west_east":
            orientation_label = "Süd West/Süd Ost"
        if "roof_direction" in offer.data and offer.data["roof_direction"] == "south":
            orientation_label = "Süd"
        if "roofs" in offer.data:
            orientation_labels = []
            pv_efficiancy = 0
            count_modules = 0
            for roof in offer.data["roofs"]:
                if "pv_count_modules" not in roof or roof["pv_count_modules"] == "":
                    roof["pv_count_modules"] = 0
                count_modules = count_modules + int(roof["pv_count_modules"])
            for roof in offer.data["roofs"]:
                roof_label, roof_efficiancy = roof_direction_values(roof["direction"], settings["data"]["wi_settings"]["pv_efficiancy"])
                if offer is not None and offer.reseller is not None and offer.reseller.document_style == "bsh" and roof.get("pv_efficiancy", "") != "":
                    roof_efficiancy = int(roof.get("pv_efficiancy", 600))
                if "pv_count_modules" not in roof or roof["pv_count_modules"] == "":
                    roof["pv_count_modules"] = 0
                roof_percent = int(roof["pv_count_modules"]) / count_modules
                orientation_labels.append(f"{int(roof_percent * 100)}% {roof_label}")
                pv_efficiancy = int(pv_efficiancy + roof_efficiancy * roof_percent)
            orientation_label = ", ".join(orientation_labels)
        if "extra_options" in offer.data and "solaredge" in offer.data["extra_options"]:
            pv_efficiancy = int(pv_efficiancy * 1.06)

        cloud_total = cloud_calulation["cloud_price_incl_refund"]
        if "emove_tarif" in offer.data:
            emove_tarif = offer.data["emove_tarif"]
        cloud_zero = False
    else:
        cloud_runtime = 12
        cloud_total = 0
        cloud_zero = False
        if "pv_options" in offer.survey.data:
            for option in offer.survey.data["pv_options"]:
                if option["label"] == "ZERO-Paket" and "is_selected" in option and option["is_selected"]:
                    cloud_zero = True

        cloud_calulation = cloud_offer_calculation_by_pv_offer(offer)
        if "cloud_emove" in offer.survey.data:
            emove_tarif = offer.survey.data["cloud_emove"]
        cloud_total = cloud_calulation["cloud_price_incl_refund"]
        if cloud_zero:
            cloud_total = cloud_total - cloud_calulation["cloud_price_light"]
            cloud_calulation["cloud_price_light_incl_refund"] = cloud_calulation["cloud_price_light_incl_refund"] - cloud_calulation["cloud_price_light"]
            cloud_calulation["cloud_price_light"] = 0
        consumer = 1
        if "has_extra_drains" in offer.survey.data and offer.survey.data["has_extra_drains"]:
            for drain in offer.survey.data["extra_drains"]:
                if "usage" in drain and drain["usage"] != "" and int(drain["usage"]) > 0:
                    consumer = consumer + 1
        orientation_label = "West/Ost"
        pv_efficiancy = settings["data"]["wi_settings"]["pv_efficiancy"]["west_east"]
        if "direction" in offer.survey.data["roof_datas"][0]:
            if offer.survey.data["roof_datas"][0]["direction"] == "south":
                orientation_label = "Süd"
                pv_efficiancy = settings["data"]["wi_settings"]["pv_efficiancy"]["south"]
            if offer.survey.data["roof_datas"][0]["direction"] == "north":
                orientation_label = "Nord"
                pv_efficiancy = settings["data"]["wi_settings"]["pv_efficiancy"]["north"]
        else:
            offer.survey.data["roof_datas"][0]["direction"] = "west"

        usage = float(offer.survey.data["pv_usage"])
        if "has_extra_drains" in offer.survey.data and offer.survey.data["has_extra_drains"]:
            for drain in offer.survey.data["extra_drains"]:
                if "usage" in drain and drain["usage"] != "" and int(drain["usage"]) > 0:
                    usage = usage + float(drain["usage"])
        heatcloud_usage = 0
        ecloud_usage = 0
        run_time = 30
        if "run_time" in offer.survey.data:
            run_time = int(offer.survey.data["run_time"])
        price_increase = 5.75
        if "price_increase" in offer.survey.data:
            price_increase = float(offer.survey.data["price_increase"])
        inflation_rate = 2.5
        if "inflation_rate" in offer.survey.data:
            inflation_rate = float(offer.survey.data["inflation_rate"])
        packet = int(offer.survey.data["packet_number"])
        orientation = offer.survey.data["roof_datas"][0]["direction"]
        orientation_label = "Süd" if offer.survey.data["roof_datas"][0]["direction"] == "south" else "West/Ost"
    data = {
        "cloud_runtime": cloud_runtime,
        "runtime": run_time,
        "cloud_zero": cloud_zero,
        "usage": usage,
        "heatcloud_usage": heatcloud_usage,
        "ecloud_usage": ecloud_usage,
        "usage": usage,
        "paket": packet,
        "pv_efficiancy": pv_efficiancy,
        "orientation": orientation,
        "orientation_label": orientation_label,
        "investment_type": investment_type,
        "in_use_date": in_use_date,
        "conventional_base_cost_per_year": settings["data"]["wi_settings"]["conventional_base_cost_per_year"],
        "conventional_base_cost_per_kwh": settings["data"]["cloud_settings"]["lightcloud_extra_price_per_kwh"],
        "conventional_gas_cost_per_kwh": 0.0598,
        "conventional_heat_cost_per_kwh": 0.23,
        "cost_increase_rate": price_increase,
        "cost_increase_rate_heat": price_increase_heat,
        "cost_increase_rate_ecloud": price_increase_ecloud,
        "cost_increase_rate_emove": price_increase_emove,
        "inflation_rate": inflation_rate,
        "full_cost_increase_rate": price_increase + inflation_rate,
        "full_cost_increase_rate_heat": price_increase_heat + inflation_rate,
        "full_cost_increase_rate_ecloud": price_increase_ecloud + inflation_rate,
        "full_cost_increase_rate_emove": price_increase_emove + inflation_rate,
        "conventional_total_cost": None,
        "consumer_count": consumer,
        "cloud_monthly_cost": cloud_total,
        "eeg_refund_per_kwh": float(settings["data"]["wi_settings"]["eeg_refund_per_kwh"]),
        "refund_per_kwh": settings["data"]["wi_settings"]["refund_per_kwh"],
        "pv_offer_total": pv_offer_total,
        "loan_interest_rate": settings["data"]["wi_settings"]["loan_interest_rate"],
        "cloud_calulation": cloud_calulation,
        "loan_total": None,
        "cloud_total": None,
        "cost_total": None,
        "cost_benefit": None
    }
    if loan_interest_rate is not None:
        data["loan_interest_rate"] = loan_interest_rate
    data["conventional_base_cost_per_kwh"] = cloud_calulation["conventional_power_cost_per_kwh"] * 100
    if offer.data is not None and "conventional_power_cost_per_kwh" in offer.data and offer.data["conventional_power_cost_per_kwh"] is not None and offer.data["conventional_power_cost_per_kwh"] != "":
        data["conventional_base_cost_per_kwh"] = float(offer.data["conventional_power_cost_per_kwh"]) / 100
    if offer.data is not None and "conventional_gas_cost_per_kwh" in offer.data and offer.data["conventional_gas_cost_per_kwh"] is not None and offer.data["conventional_gas_cost_per_kwh"] != "":
        data["conventional_gas_cost_per_kwh"] = float(offer.data["conventional_gas_cost_per_kwh"]) / 100
    if offer.data is not None and "conventional_heat_cost_per_kwh" in offer.data and offer.data["conventional_heat_cost_per_kwh"] is not None and offer.data["conventional_heat_cost_per_kwh"] != "":
        data["conventional_heat_cost_per_kwh"] = float(offer.data["conventional_heat_cost_per_kwh"]) / 100
    if data["investment_type"] == "cash":
        data["loan_interest_rate"] = 0
    data["eeg_refund_per_kwh"] = 0.0808
    refund_rate = None
    if "pv_kwp" in cloud_calulation and cloud_calulation["pv_kwp"] > 0:
        refund_rate = EEGRefundRate.query\
            .filter(EEGRefundRate.month == offer.datetime.month)\
            .filter(EEGRefundRate.year == offer.datetime.year)\
            .filter(EEGRefundRate.min_kwp < cloud_calulation["pv_kwp"])\
            .filter(EEGRefundRate.max_kwp >= cloud_calulation["pv_kwp"])\
            .order_by(EEGRefundRate.value.asc())\
            .first()
        if refund_rate is not None:
            data["eeg_refund_per_kwh"] = refund_rate.value
    if refund_rate is None:
        if "min_kwp" in cloud_calulation and cloud_calulation["min_kwp"] > 0:
            refund_rate = EEGRefundRate.query\
                .filter(EEGRefundRate.month == offer.datetime.month)\
                .filter(EEGRefundRate.year == offer.datetime.year)\
                .filter(EEGRefundRate.min_kwp < cloud_calulation["min_kwp"])\
                .filter(EEGRefundRate.max_kwp >= cloud_calulation["min_kwp"])\
                .order_by(EEGRefundRate.value.asc())\
                .first()
            if refund_rate is not None:
                data["eeg_refund_per_kwh"] = refund_rate.value
        else:
            refund_rate = EEGRefundRate.query\
                .filter(EEGRefundRate.month == offer.datetime.month)\
                .filter(EEGRefundRate.year == offer.datetime.year)\
                .order_by(EEGRefundRate.value.asc())\
                .first()
            if refund_rate is not None:
                data["eeg_refund_per_kwh"] = refund_rate.value

    if offer.data is not None and "loan_total" in offer.data and offer.data["loan_total"] is not None and offer.data["loan_total"] != "":
        data["pv_offer_total"] = float(offer.data["loan_total"])
    if offer.data is not None and "total_net" in offer.data and offer.data["total_net"] is not None and offer.data["total_net"] != "":
        data["pv_offer_total"] = float(offer.data["total_net"])
    yearly_loan_payment = data["pv_offer_total"] / 20
    if data["loan_interest_rate"] > 0:
        yearly_loan_payment = (data["pv_offer_total"] * data["loan_interest_rate"] / 100) / (1 - (1 + data["loan_interest_rate"] / 100) ** -20)
    data["loan_total_interest"] = 0
    rest_loan = data["pv_offer_total"]
    for n in range(20):
        interest = rest_loan * (data["loan_interest_rate"] / 100)
        data["loan_total_interest"] = data["loan_total_interest"] + interest
        rest_loan = rest_loan + interest - yearly_loan_payment
    data["loan_total"] = data["loan_total_interest"] + data["pv_offer_total"]
    data["conventional_usage_cost"] = data["conventional_base_cost_per_kwh"] * float(data["usage"])

    base = data["conventional_usage_cost"] + data["conventional_base_cost_per_year"]
    base_base = data["conventional_base_cost_per_year"]
    base_usage = data["conventional_usage_cost"]

    data["total_pages"] = 17
    data["lightcloud"] = {
        "price_today": cloud_calulation["conventional_price_light"] + cloud_calulation["conventional_price_consumer"],
        "price_tomorrow": float(cloud_calulation["cloud_price_light_incl_refund"]) + float(cloud_calulation["cloud_price_consumer_incl_refund"])
    }
    data["lightcloud"]["price_half_time"] = data["lightcloud"]["price_today"] * (1 + data["full_cost_increase_rate"] / 100) ** (data["cloud_runtime"] / 2)
    data["lightcloud"]["price_full_time"] = data["lightcloud"]["price_today"] * (1 + data["full_cost_increase_rate"] / 100) ** data["cloud_runtime"]
    data["lightcloud"]["max_value"] = data["lightcloud"]["price_full_time"]
    if data["lightcloud"]["price_tomorrow"] < 0:
        data["lightcloud"]["max_value"] = data["lightcloud"]["max_value"] - data["lightcloud"]["price_tomorrow"]
    data["lightcloud"]["price_runtime"] = 0
    for i in range(data["runtime"]):
        data["lightcloud"]["price_runtime"] = data["lightcloud"]["price_runtime"] + ((cloud_calulation["conventional_price_light"]) * (1 + data["full_cost_increase_rate"] / 100) ** i) * 12

    if cloud_calulation["conventional_price_consumer"] > 0:
        data["consumer"] = {"price_runtime": 0}
        for i in range(data["runtime"]):
            data["consumer"]["price_runtime"] = data["consumer"]["price_runtime"] + (cloud_calulation["conventional_price_consumer"] * (1 + data["full_cost_increase_rate"] / 100) ** i) * 12

    if cloud_calulation["cloud_price_ecloud"] > 0:
        data["total_pages"] = data["total_pages"] + 1
        data["ecloud"] = {
            "price_today": (cloud_calulation["ecloud_usage"] * data["conventional_gas_cost_per_kwh"]) / 12,
            "price_tomorrow": cloud_calulation["cloud_price_ecloud_incl_refund"]
        }
        base = base + data["ecloud"]["price_today"] * 12
        data["ecloud"]["price_half_time"] = data["ecloud"]["price_today"] * (1 + data["full_cost_increase_rate_ecloud"] / 100) ** (data["cloud_runtime"] / 2)
        data["ecloud"]["price_full_time"] = data["ecloud"]["price_today"] * (1 + data["full_cost_increase_rate_ecloud"] / 100) ** data["cloud_runtime"]
        data["ecloud"]["price_runtime"] = 0
        for i in range(data["runtime"]):
            data["ecloud"]["price_runtime"] = data["ecloud"]["price_runtime"] + (data["ecloud"]["price_today"] * (1 + data["full_cost_increase_rate_ecloud"] / 100) ** i) * 12
        data["ecloud"]["max_value"] = data["ecloud"]["price_full_time"]
        if data["ecloud"]["price_tomorrow"] < 0:
            data["ecloud"]["max_value"] = data["ecloud"]["max_value"] - data["ecloud"]["price_tomorrow"]
    if cloud_calulation["cloud_price_heatcloud"] > 0:
        data["consumer_count"] = data["consumer_count"] + 1
        data["total_pages"] = data["total_pages"] + 1
        data["heatcloud"] = {
            "price_today": (cloud_calulation["heater_usage"] * data["conventional_heat_cost_per_kwh"]) / 12,
            "price_tomorrow": cloud_calulation["cloud_price_heatcloud_incl_refund"]
        }
        base = base + data["heatcloud"]["price_today"] * 12
        data["heatcloud"]["price_half_time"] = data["heatcloud"]["price_today"] * (1 + data["full_cost_increase_rate_heat"] / 100) ** (data["cloud_runtime"] / 2)
        data["heatcloud"]["price_full_time"] = data["heatcloud"]["price_today"] * (1 + data["full_cost_increase_rate_heat"] / 100) ** data["cloud_runtime"]
        data["heatcloud"]["price_runtime"] = 0
        for i in range(data["runtime"]):
            data["heatcloud"]["price_runtime"] = data["heatcloud"]["price_runtime"] + (data["heatcloud"]["price_today"] * (1 + data["full_cost_increase_rate_heat"] / 100) ** i) * 12
        data["heatcloud"]["max_value"] = data["heatcloud"]["price_full_time"]
        if data["heatcloud"]["price_tomorrow"] < 0:
            data["heatcloud"]["max_value"] = data["heatcloud"]["max_value"] - data["heatcloud"]["price_tomorrow"]
    if cloud_calulation["cloud_price_emove"] > 0:
        data["total_pages"] = data["total_pages"] + 1
        data["emove"] = {
            "price_today": 0,
            "price_tomorrow": cloud_calulation["cloud_price_emove"]
        }
        if emove_tarif == "emove.drive I":
            data["emove"]["price_today"] = 8000 / 100 * 7 * 1.19 / 12
        if emove_tarif == "emove.drive II":
            data["emove"]["price_today"] = 12000 / 100 * 7 * 1.19 / 12
        if emove_tarif == "emove.drive III":
            data["emove"]["price_today"] = 20000 / 100 * 7 * 1.19 / 12
        if emove_tarif == "emove.drive ALL":
            data["emove"]["price_today"] = 25000 / 100 * 7 * 1.19 / 12
        base = base + data["emove"]["price_today"] * 12
        data["emove"]["price_half_time"] = data["emove"]["price_today"] * (1 + data["full_cost_increase_rate_emove"] / 100) ** (data["cloud_runtime"] / 2)
        data["emove"]["price_full_time"] = data["emove"]["price_today"] * (1 + data["full_cost_increase_rate_emove"] / 100) ** data["cloud_runtime"]
        data["emove"]["price_runtime"] = 0
        for i in range(data["runtime"]):
            data["emove"]["price_runtime"] = data["emove"]["price_runtime"] + (data["emove"]["price_today"] * (1 + data["full_cost_increase_rate_emove"] / 100) ** i) * 12
        data["emove"]["max_value"] = data["emove"]["price_full_time"]
        if data["emove"]["price_tomorrow"] < 0:
            data["emove"]["max_value"] = data["emove"]["max_value"] - data["emove"]["price_tomorrow"]
    data["conventional_total_usage_cost"] = data["conventional_usage_cost"]
    for n in range(data["runtime"]):
        data["conventional_total_usage_cost"] = data["conventional_total_usage_cost"] + data["conventional_total_usage_cost"] * ((1 + data["full_cost_increase_rate"] / 100) ** data["runtime"])

    data["conventional_total_base_cost"] = data["conventional_base_cost_per_year"]
    for n in range(data["runtime"]):
        data["conventional_total_base_cost"] = data["conventional_total_base_cost"] + data["conventional_total_base_cost"] * ((1 + data["full_cost_increase_rate"] / 100) ** data["runtime"])

    data["conventional_total_cost_base"] = 0
    data["conventional_total_cost_usage"] = 0
    for n in range(data["runtime"]):
        data["conventional_total_cost_base"] = data["conventional_total_cost_base"] + base_base
        data["conventional_total_cost_usage"] = data["conventional_total_cost_usage"] + base_usage
        base = base * (1 + data["full_cost_increase_rate"] / 100)
        base_base = base_base * (1 + data["full_cost_increase_rate"] / 100)
        base_usage = base_usage * (1 + data["full_cost_increase_rate"] / 100)

    data["conventional_total_cost"] = data["lightcloud"]["price_runtime"]
    if "consumer" in data:
        data["conventional_total_cost"] = data["conventional_total_cost"] + data["consumer"]["price_runtime"]
    if "heatcloud" in data:
        data["conventional_total_cost"] = data["conventional_total_cost"] + data["heatcloud"]["price_runtime"]
    if "ecloud" in data:
        data["conventional_total_cost"] = data["conventional_total_cost"] + data["ecloud"]["price_runtime"]
    if "emove" in data:
        data["conventional_total_cost"] = data["conventional_total_cost"] + data["emove"]["price_runtime"]

    repair_cost_yearly = data["loan_total"] * 0.08
    if repair_cost_yearly > 4500:
        repair_cost_yearly = 4500
    # 5.88 for remote care cost
    data["cloud_total"] = (data["cloud_monthly_cost"] + 5.88) * 12 * int(cloud_runtime)
    for i in range(data["runtime"] - int(cloud_runtime)):
        cloud_new_rate = ((data["cloud_monthly_cost"] + 5.88) * 12) * (1 + data["full_cost_increase_rate"] / 100) ** (i + 1)
        if cloud_new_rate < 0:
            cloud_new_rate = -cloud_new_rate + 2 * (data["cloud_monthly_cost"] * 12)
        data["cloud_total"] = data["cloud_total"] + cloud_new_rate

    data["maintainance_cost_yearly"] = 110
    if offer.reseller is not None and offer.reseller.document_style == "bsh":
        data["insurance_cost_yearly"] = 85
        if 50000 < data["pv_offer_total"] <= 80000:
            data["insurance_cost_yearly"] = 130
        if 80000 < data["pv_offer_total"]:
            data["insurance_cost_yearly"] = 200

        repair_cost_yearly = data["pv_offer_total"] * 0.10
        if "pv_kwp" in cloud_calulation:
            if 15 < cloud_calulation["pv_kwp"] <= 30:
                data["maintainance_cost_yearly"] = int(7.5 * cloud_calulation["pv_kwp"])
            if 30 < cloud_calulation["pv_kwp"] <= 50:
                data["maintainance_cost_yearly"] = int(6.5 * cloud_calulation["pv_kwp"])
            if 50 < cloud_calulation["pv_kwp"] <= 200:
                data["maintainance_cost_yearly"] = int(5.5 * cloud_calulation["pv_kwp"])
            if 200 < cloud_calulation["pv_kwp"]:
                data["maintainance_cost_yearly"] = int(4.5 * cloud_calulation["pv_kwp"])
        data["cloud_total"] = ((data["cloud_monthly_cost"] * 12) + data["maintainance_cost_yearly"] + data["insurance_cost_yearly"]) * int(cloud_runtime)
        for i in range(data["runtime"] - int(cloud_runtime)):
            cloud_new_rate = (data["cloud_monthly_cost"] * 12) * (1 + data["full_cost_increase_rate"] / 100) ** (i + 1)
            if cloud_new_rate < 0:
                cloud_new_rate = -cloud_new_rate + 2 * (data["cloud_monthly_cost"] * 12)
            cloud_new_rate = cloud_new_rate + data["maintainance_cost_yearly"] + data["insurance_cost_yearly"]
            data["cloud_total"] = data["cloud_total"] + cloud_new_rate

    data["cloud_total"] = data["cloud_total"] + repair_cost_yearly

    data["eeg_direct_usage_cost"] = 0
    if "pv_kwp" in data["cloud_calulation"] and data["cloud_calulation"]["pv_kwp"] >= 30:
        data["eeg_direct_usage_cost"] = cloud_calulation["power_usage"] * 0.6 * (0.06756 / 2) * data["runtime"]
        data["cloud_total"] = data["cloud_total"] + data["eeg_direct_usage_cost"]
    data["cost_total"] = data["cloud_total"] + data["loan_total"]
    data["cost_benefit"] = data["conventional_total_cost"] - data["cost_total"]
    max_cost = data["conventional_total_cost"]
    if data["cost_total"] > max_cost:
        max_cost = data["cost_total"]
    data["cost_conventional_rate"] = data["conventional_total_cost"] / max_cost
    data["cost_cloud_rate"] = data["cost_total"] / max_cost
    return data


def generate_feasibility_study_2020_pdf(offer: OfferV2, return_string=False):
    settings = get_settings("pv-settings")
    if settings is None:
        return None
    data = calculate_feasibility_study(offer)
    data["base_url"] = "https://api.korbacher-energiezentrum.de"
    content = render_template("feasibility_study_2020/index.html", offer=offer, data=data, settings=settings)
    pdf = gotenberg_pdf(content, landscape=True, margins=[0, 0, 0, 0], wait_delay="0.2")
    temp_pdf_file_output = tempfile.NamedTemporaryFile()
    temp_pdf_file_input = tempfile.NamedTemporaryFile()
    temp_pdf_file_input.write(pdf)
    process = subprocess.Popen([
        'gs',
        '-sDEVICE=pdfwrite',
        '-dCompatibilityLevel=1.4',
        '-dPDFSETTINGS=/prepress',
        '-dNOPAUSE',
        '-dQUIET',
        '-dBATCH',
        f'-sOutputFile={temp_pdf_file_output.name}',
        temp_pdf_file_input.name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    temp_pdf_file_input.close()
    temp_pdf_file_output.seek(0)
    pdf = temp_pdf_file_output.read()
    temp_pdf_file_output.close()
    if return_string:
        response = make_response(content)
        response.headers['Content-Type'] = 'text/html'
        return response
    if pdf:
        pdf_file = S3File.query\
            .filter(S3File.model == "OfferV2FeasibilityStudy")\
            .filter(S3File.model_id == offer.id)\
            .first()
        file_data = {
            "model": "OfferV2FeasibilityStudy",
            "model_id": offer.id,
            "prepend_path": f"Angebot {offer.id}/",
            "content-type": 'application/pdf',
            "file_content": pdf,
            "filename": f"Wirtschaftlichkeitsrechnung PV-{offer.id}.pdf"
        }
        if pdf_file is not None:
            update_file(pdf_file.id, file_data)
        else:
            add_file(file_data)
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        return response
    response = make_response("pdf generation failed")
    response.headers['Content-Type'] = 'text/html'
    return response


def generate_feasibility_study_pdf(offer: OfferV2, return_string=False):
    return generate_feasibility_study_2020_pdf(offer, return_string=return_string)
    settings = get_settings("pv-settings")
    if settings is None:
        return None
    data = calculate_feasibility_study(offer)

    content = render_template("feasibility_study/overlay.html", offer=offer, data=data, settings=settings)
    if return_string:
        response = make_response(content)
        response.headers['Content-Type'] = 'text/html'
        return response
    config = pdfkit.configuration(wkhtmltopdf="./wkhtmltopdf")
    overlay_binary = pdfkit.from_string(content, configuration=config, output_path=False, options={
        'disable-smart-shrinking': ''
    })
    if overlay_binary is not None:
        pdf = BytesIO()
        output = PdfFileWriter()
        base_study_pdf = PdfFileReader(open("app/modules/offer/static/feasibility_study.pdf", 'rb'))
        overlay_pdf = PdfFileReader(BytesIO(overlay_binary))
        i2 = 0
        extra_pages = 0
        extra_pages2 = 0
        extra_pages3 = 0
        for i in range(data["total_pages"]):
            if i == 7:
                page = base_study_pdf.getPage(16)
            elif i == 8 and "ecloud" in data:
                page = base_study_pdf.getPage(17)
                extra_pages = extra_pages + 1
            elif i == 8 + extra_pages and "heatcloud" in data:
                page = base_study_pdf.getPage(18)
                extra_pages2 = extra_pages2 + 1
            elif i == 8 + extra_pages + extra_pages2 and "emove" in data:
                page = base_study_pdf.getPage(19)
                extra_pages3 = extra_pages3 + 1
            else:
                page = base_study_pdf.getPage(i2)
                i2 = i2 + 1
            page.mergePage(overlay_pdf.getPage(i))
            output.addPage(page)
        output.write(pdf)
        pdf.seek(0)
        pdf_file = S3File.query\
            .filter(S3File.model == "OfferV2FeasibilityStudy")\
            .filter(S3File.model_id == offer.id)\
            .first()
        file_data = {
            "model": "OfferV2FeasibilityStudy",
            "model_id": offer.id,
            "prepend_path": f"Angebot {offer.id}/",
            "content-type": 'application/pdf',
            "file": pdf,
            "filename": f"Wirtschaftlichkeitsrechnung PV-{offer.id}.pdf"
        }
        if pdf_file is not None:
            update_file(pdf_file.id, file_data)
        else:
            add_file(file_data)
        pdf.seek(0)
        response = make_response(pdf.read())
        response.headers['Content-Type'] = 'application/pdf'
        return response


def roof_direction_values(direction, settings):
    orientation_label = "West/Ost"
    if direction == "north":
        orientation_label = "Nord"
    if direction == "north_west":
        orientation_label = "Nord West"
    if direction == "north_east":
        orientation_label = "Nord Ost"
    if direction == "north_west_east":
        orientation_label = "Nord West/Nord Ost"
    if direction == "north_south":
        orientation_label = "Nord/Süd"
    if direction == "west":
        orientation_label = "West"
    if direction == "east":
        orientation_label = "Ost"
    if direction == "west_east":
        orientation_label = "West/Ost"
    if direction == "south_west":
        orientation_label = "Süd West"
    if direction == "south_east":
        orientation_label = "Süd Ost"
    if direction == "south_west_east":
        orientation_label = "Süd West/Süd Ost"
    if direction == "south":
        orientation_label = "Süd"
    return orientation_label, settings[direction]
