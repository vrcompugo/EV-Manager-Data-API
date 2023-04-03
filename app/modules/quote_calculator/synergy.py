import json
import math
import io
import datetime
from flask import render_template
from PyPDF2 import PdfFileMerger, PdfFileWriter, PdfFileReader

from app.modules.settings import get_settings
from app.modules.external.bitrix24.drive import get_file_content_cached
from app.utils.gotenberg import gotenberg_pdf


def calculate_synergy_wi(data):
    if data.get("pv_kwp", 0) in [None, "", 0]:
        return data
    calculated = {
        "runtime": 25,
        "storage_size": 0,
        "pv_kwp": 0,
        "cloud_price": 0,
        "cloud_price_incl_refund": 0,
        "power_usage": 0,
        "power_extra_usage": 0,
        "heater_usage": 0,
        "consumer_usage": 0,
        "total_light_usage": 0,
        "total_usage": 0,
        "pv_production": 0,
        "conventional_price_light": 0,
        "conventional_price_heatcloud": 0,
        "conventional_price_consumer": 0,
        "conventional_power_cost_per_kwh": 0.39,
        "conventional_heating_cost_per_kwh": 0.29,
        "pv_efficiancy": 0,
        "autocracy_rate": 71,
        "direct_market_cashback": 0.12,
        "direct_usage_cashback": 0.1 / 12,
        "eeg_cashback": 0.08,
        "total_cost_runtime": 0,
        "total_cost_runtime_conventional": 0,
        "power_increase_rate": 3.75,
        "heating_increase_rate": 4.00,
        "inflation_rate": 1.00,
        "total_price_increase_rate": 0,
        "financing_rate": 3.99,
        "conventional_cost_light_monthly_today": 0,
        "conventional_cost_light_monthly_10years": 0,
        "conventional_cost_light_monthly_20years": 0,
        "conventional_cost_heating_monthly_today": 0,
        "conventional_cost_heating_monthly_10years": 0,
        "conventional_cost_heating_monthly_20years": 0,
        "conventional_cost_monthly_today": 0,
        "conventional_cost_monthly_10years": 0,
        "conventional_cost_monthly_20years": 0,
        "investment_cost_total": 0,
        "direct_usage": 0,
        "direct_usage_bonus": 0,
        "net_usage": 0,
        "net_usage_cost": 0,
        "feeding_amount": 0,
        "feeding_amount_bonus": 0,
        "feeding_amount_bonus_monthly": 0,
        "synergy_monthly_today": 0,
        "synergy_monthly_10years": 0,
        "synergy_monthly_20years": 0,
        "lightcloud_extra_price_per_kwh": 0.39,
        "heatcloud_extra_price_per_kwh": 0.29,
        "maintainance_rate": 0.065,
        "min_kwp": 0,
        "min_kwp_light": 0,
        "extra_stacks": 0,
        "extra_synergy_bonus": 0,

        "pricing_options": [],
        "cashback_price_per_kwh": 0,
        "errors": [],
        "invalid_form": False,
        "kwp_extra": 0,
        "ecloud_usage": 0,
        "refresh_usage": 0,
        "power_extra_usage": 0,
        "min_kwp_heatcloud": 0,
        "min_kwp_ecloud": 0,
        "min_kwp_emove": 0,
        "min_kwp_consumer": 0,
        "min_kwp_refresh": 0,
        "cloud_price_extra": 0,
        "cloud_price_light": 0,
        "cloud_price_light_incl_refund": 0,
        "cloud_price_light_extra": 0,
        "cloud_price_heatcloud": 0,
        "cloud_price_heatcloud_incl_refund": 0.0,
        "cloud_price_ecloud": 0,
        "cloud_price_ecloud_incl_refund": 0.0,
        "cloud_price_emove": 0,
        "cloud_price_emove_incl_refund": 0,
        "cloud_price_consumer": 0,
        "cloud_price_consumer_incl_refund": 0.0,
        "user_one_time_cost": 0,
        "conventional_price_ecloud": 0,
        "storage_usage": 0,
        "min_storage_size": 0,
        "conventional_price_emove": 0,
        "emove_usage": 0,
        "min_zero_kwp": 0,
        "cloud_price_extra_light": 0,
        "cloud_price_extra_heatcloud": 0.0,
        "cloud_price_extra_ecloud": 0.0,
        "cloud_price_extra_consumer": 0.0,
        "cloud_price_extra_emove": 0,
        "conventional_price": 0,
        "max_kwp": 0
    }
    pv_efficiancy_values = {
        "south": 912,
        "west_east": 867,
        "south_west_east": 700,
        "north_west_east": 680,
        "north": 603
    }
    for field in ["pv_kwp", "autocracy_rate", "power_usage", "power_extra_usage", "heater_usage", "consumer_usage"]:
        if data.get(field) not in [None, "", 0]:
            calculated[field] = float(data.get(field))
    calculated["power_usage"] = calculated["power_usage"] + calculated["power_extra_usage"]
    calculated["power_extra_usage"] = 0
    calculated["total_usage"] = 0
    for field in ["power_usage", "power_extra_usage", "heater_usage", "consumer_usage"]:
        if data.get(field) not in [None, "", 0]:
            calculated["total_usage"] = calculated["total_usage"] + calculated[field]
    calculated["total_light_usage"] = calculated["total_usage"] - calculated["heater_usage"]
    calculated["min_kwp"] = calculated["total_usage"] * 1.5 / 1000
    if calculated["heater_usage"] > 0:
        calculated["min_kwp"] = calculated["total_usage"] * 1.825 / 1000
    calculated["min_kwp_light"] = calculated["min_kwp"]
    if calculated["min_kwp"] < calculated["pv_kwp"]:
        calculated["max_kwp"] = calculated["min_kwp"]
        calculated["kwp_extra"] = calculated["pv_kwp"] - calculated["max_kwp"]
        if calculated["kwp_extra"] > 1:
            percent_kwp = calculated["min_kwp"] / calculated["pv_kwp"]
            calculated["autocracy_rate"] = math.floor(calculated["autocracy_rate"] + (100 - calculated["autocracy_rate"]) * percent_kwp * 0.06)
            if calculated["autocracy_rate"] > 100:
                calculated["autocracy_rate"] = 100
    else:
        calculated["max_kwp"] = calculated["pv_kwp"]
        calculated["kwp_extra"] = calculated["max_kwp"] - calculated["min_kwp"]
        percent_kwp = calculated["pv_kwp"] / calculated["min_kwp"]
        calculated["autocracy_rate"] = math.floor(calculated["autocracy_rate"] * (1.25*percent_kwp**3 - 3.3*percent_kwp**2 + 3.05*percent_kwp))

    size = 0
    if calculated["power_usage"] not in [None, "", 0, "0"]:
        size = size + math.ceil(calculated["power_usage"] / 4200) * 4.2
    if calculated["heater_usage"] not in [None, "", 0, "0"]:
        size = size + math.ceil(calculated["heater_usage"] / 9000) * 4.2
    size = 0
    if 0 < calculated["total_usage"] <= 8000:
        size = 8.4
    if 8000 < calculated["total_usage"] <= 12300:
        size = 12.6
    if 12300 < calculated["total_usage"] <= 16600:
        size = 16.8
    if 16600 < calculated["total_usage"] <= 21000:
        size = 21
    if 21000 < calculated["total_usage"]:
        size = 25.2
    if 26000 < calculated["total_usage"]:
        raise Exception("storage produkt could not be calculated")
    calculated["min_storage_size"] = size
    calculated["storage_size"] = size
    if data.get("overwrite_storage_size") not in [None, 0, ""]:
        calculated["storage_size"] = float(data.get("overwrite_storage_size"))
    if calculated["storage_size"] > calculated["min_storage_size"]:
        calculated["extra_stacks"] = math.floor((calculated["storage_size"] - calculated["min_storage_size"]) / 4.2)
        calculated["autocracy_rate"] = calculated["autocracy_rate"] + 7
        calculated["extra_synergy_bonus"] = calculated["extra_synergy_bonus"] + 35
        if calculated["extra_stacks"] > 1:
            calculated["autocracy_rate"] = calculated["autocracy_rate"] + (calculated["extra_stacks"] - 1) * 1.5
            calculated["extra_synergy_bonus"] = calculated["extra_synergy_bonus"] + (calculated["extra_stacks"] - 1) * 35
    if calculated["autocracy_rate"] > 100:
        calculated["autocracy_rate"] = 100
    calculated["power_total_increase_rate"] = calculated["inflation_rate"] + calculated["power_increase_rate"]
    calculated["heating_total_increase_rate"] = calculated["inflation_rate"] + calculated["heating_increase_rate"]
    if "roofs" in data:
        orientation_labels = []
        pv_efficiancy = 0
        count_modules = 0
        for roof in data["roofs"]:
            if "pv_count_modules" not in roof or roof["pv_count_modules"] == "":
                roof["pv_count_modules"] = 0
            count_modules = count_modules + int(roof["pv_count_modules"])
        for roof in data["roofs"]:
            roof_label = roof_direction_values(roof["direction"])
            roof_efficiancy = pv_efficiancy_values[roof["direction"]]
            if "pv_count_modules" not in roof or roof["pv_count_modules"] == "":
                roof["pv_count_modules"] = 0
            roof_percent = int(roof["pv_count_modules"]) / count_modules
            orientation_labels.append(f"{int(roof_percent * 100)}% {roof_label}")
            pv_efficiancy = round(pv_efficiancy + roof_efficiancy * roof_percent)
        orientation_label = ", ".join(orientation_labels)
        calculated["orientation_label"] = orientation_label
        calculated["pv_efficiancy"] = pv_efficiancy
    calculated["pv_production"] = calculated["pv_kwp"] * calculated["pv_efficiancy"]
    calculated["direct_usage"] = calculated["total_usage"] * (calculated["autocracy_rate"] / 100)
    calculated["synergy_bonus_monthly"] = calculated["direct_usage"] * calculated["direct_usage_cashback"]
    if calculated["synergy_bonus_monthly"] < 12:
        calculated["synergy_bonus_monthly"] = 12
    if calculated["synergy_bonus_monthly"] > 55:
        calculated["synergy_bonus_monthly"] = 55
    calculated["synergy_bonus_monthly"] = calculated["synergy_bonus_monthly"] + calculated["extra_synergy_bonus"]
    calculated["synergy_bonus"] = calculated["synergy_bonus_monthly"] * 12
    calculated["net_usage"] = calculated["total_usage"] - calculated["direct_usage"]
    calculated["net_usage_cost"] = calculated["net_usage"] * calculated["lightcloud_extra_price_per_kwh"]
    calculated["net_usage_cost_monthly"] = calculated["net_usage_cost"] / 12
    calculated["feeding_amount"] = calculated["pv_production"] - calculated["direct_usage"]
    calculated["feeding_amount_bonus"] = calculated["feeding_amount"] * calculated["eeg_cashback"]
    calculated["feeding_amount_bonus_monthly"] = calculated["feeding_amount_bonus"] / 12
    calculated["synergy_monthly_today"] = calculated["net_usage_cost_monthly"] - calculated["synergy_bonus_monthly"] - calculated["feeding_amount_bonus_monthly"]
    calculated["synergy_monthly_10years"] = calculated["net_usage_cost_monthly"] * (1 + calculated["power_total_increase_rate"] / 100) ** 10 - calculated["synergy_bonus_monthly"] - calculated["feeding_amount_bonus_monthly"]
    calculated["synergy_monthly_20years"] = calculated["net_usage_cost_monthly"] * (1 + calculated["power_total_increase_rate"] / 100) ** 20 - calculated["synergy_bonus_monthly"] - calculated["feeding_amount_bonus_monthly"]
    calculated["conventional_cost_light_monthly_today"] = (calculated["total_light_usage"] * calculated["conventional_power_cost_per_kwh"]) / 12
    calculated["conventional_cost_heating_monthly_today"] = (calculated["heater_usage"] * calculated["conventional_heating_cost_per_kwh"]) / 12
    calculated["conventional_cost_monthly_today"] = calculated["conventional_cost_light_monthly_today"] + calculated["conventional_cost_heating_monthly_today"]
    calculated["conventional_cost_light_monthly_10years"] = calculated["conventional_cost_light_monthly_today"] * (1 + calculated["power_total_increase_rate"] / 100) ** 10
    calculated["conventional_cost_heating_monthly_10years"] = calculated["conventional_cost_heating_monthly_today"] * (1 + calculated["heating_total_increase_rate"] / 100) ** 10
    calculated["conventional_cost_monthly_10years"] = calculated["conventional_cost_light_monthly_10years"] + calculated["conventional_cost_heating_monthly_10years"]
    calculated["conventional_cost_light_monthly_20years"] = calculated["conventional_cost_light_monthly_today"] * (1 + calculated["power_total_increase_rate"] / 100) ** 20
    calculated["conventional_cost_heating_monthly_20years"] = calculated["conventional_cost_heating_monthly_today"] * (1 + calculated["heating_total_increase_rate"] / 100) ** 20
    calculated["conventional_cost_monthly_20years"] = calculated["conventional_cost_light_monthly_20years"] + calculated["conventional_cost_heating_monthly_20years"]
    calculated["conventional_cost_light_total"] = 0
    calculated["conventional_cost_heating_total"] = 0
    calculated["conventional_cost_total"] = 0
    calculated["synergy_total"] = 0
    for i in range(calculated["runtime"]):
        calculated["conventional_cost_light_total"] = calculated["conventional_cost_light_total"] + (calculated["conventional_cost_light_monthly_today"] * (1 + calculated["power_total_increase_rate"] / 100) ** i) * 12
        calculated["conventional_cost_heating_total"] = calculated["conventional_cost_heating_total"] + (calculated["conventional_cost_heating_monthly_today"] * (1 + calculated["power_total_increase_rate"] / 100) ** i) * 12
        calculated["conventional_cost_total"] = calculated["conventional_cost_total"] + calculated["conventional_cost_light_total"] + calculated["conventional_cost_heating_total"]
        calculated["synergy_total"] = calculated["synergy_total"] + (calculated["net_usage_cost_monthly"] * (1 + calculated["power_total_increase_rate"] / 100) ** i - calculated["synergy_bonus_monthly"] - calculated["feeding_amount_bonus_monthly"]) * 12
    calculated["conventional_cost_monthly_avarage"] = (calculated["conventional_cost_monthly_today"] + calculated["conventional_cost_monthly_10years"] + calculated["conventional_cost_monthly_20years"]) / 3
    return calculated

def calculate_synergy_wi2(return_data):
    calculated = return_data["calculated"]
    calculated["maintainance_cost_yearly"] = (return_data["total_net"] * calculated["maintainance_rate"]) / calculated["runtime"]
    calculated["maintainance_cost_total"] = calculated["maintainance_cost_yearly"] * calculated["runtime"]
    total_pv_cost = calculated["maintainance_cost_total"]
    if "loan_calculation" in return_data:
        total_pv_cost = total_pv_cost + return_data["loan_calculation"]["interest_cost"]
    total_pv_cost = total_pv_cost + return_data["total_net"]
    calculated["total_pv_cost_monthly"] = total_pv_cost / (calculated["runtime"] * 12)

    calculated["synergy_monthly_today_total"] = calculated["synergy_monthly_today"] + calculated["total_pv_cost_monthly"]
    calculated["synergy_monthly_10years_total"] = calculated["synergy_monthly_10years"] + calculated["total_pv_cost_monthly"]
    calculated["synergy_monthly_20years_total"] = calculated["synergy_monthly_20years"] + calculated["total_pv_cost_monthly"]
    calculated["synergy_monthly_avarage"] = (calculated["synergy_monthly_today_total"] + calculated["synergy_monthly_10years_total"] + calculated["synergy_monthly_20years_total"]) / 3
    return return_data["calculated"]

def generate_synergy_pdf(lead_id, data):
    config_general = get_settings(section="general")
    if data is not None:
        data["base_url"] = config_general["base_url"]
        if "datetime" not in data:
            data["datetime"] = datetime.datetime.now()
        content = render_template(
            "quote_calculator/generator/synergy_wi/index.html",
            base_url=config_general["base_url"],
            lead_id=lead_id,
            data=data
        )
        data["datetime"] = str(data["datetime"])
        overlay_pdf = PdfFileReader(io.BytesIO(gotenberg_pdf(
            content,
            margins=["0", "0", "0", "0"],
            landscape=True)))
        base_pdf = PdfFileReader(io.BytesIO(get_file_content_cached(7476459)))  # https://keso.bitrix24.de/disk/downloadFile/7476459/?&ncc=1&filename=Synergie+360+WI.pdf
        pdf = PdfFileWriter()
        for i in range(0, base_pdf.getNumPages()):
            #if i not in [0]:
            #    continue
            if i in [8, 9, 11, 12]:
                page = overlay_pdf.getPage(i)
            else:
                page = overlay_pdf.getPage(i)
                page.mergePage(base_pdf.getPage(i))
            pdf.addPage(page)
        output = io.BytesIO()
        pdf.write(output)
        output.seek(0)
        return output.read()


def roof_direction_values(direction):
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
    return orientation_label