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
        "runtime": 30,
        "storage_size": 0,
        "pv_kwp": 0,
        "cloud_price": 0,
        "cloud_price_incl_refund": 0,
        "power_usage": 0,
        "power_extra_usage": 0,
        "heater_usage": 0,
        "car_usage": 0,
        "consumer_usage": 0,
        "total_light_usage": 0,
        "total_usage": 0,
        "pv_production": 0,
        "conventional_price_light": 0,
        "conventional_price_heatcloud": 0,
        "conventional_price_consumer": 0,
        "conventional_power_cost_per_kwh": 0.39,
        "conventional_heating_cost_per_kwh": 0.29,
        "conventional_car_cost_per_kwh": 0.39,
        "pv_efficiancy": 0,
        "autocracy_rate": 71,
        "max_autocracy_rate": 86.75,
        "direct_market_cashback": 0.1,
        "synergy_bonus_factor": 0.1 / 12,
        "autocracy_missing_kwp_nerf": 1.7,
        "synergy_first_missing_storage_stack_autocracy_nerf": 16,
        "synergy_first_missing_storage_stack_cash_nerf": 22,
        "synergy_missing_storage_stack_autocracy_nerf": 14,
        "synergy_missing_storage_stack_cash_nerf": 33,
        "synergy_extra_storage_stack_autocracy_bonus": 7,
        "synergy_extra_storage_stack_cash_bonus": 39,
        "synergy_extra_additional_storage_stack_autocracy_bonus": 4.75,
        "synergy_extra_additional_storage_stack_cash_bonus": 19,
        "synergy_car_bonus": 30,
        "synergy_hard_max_bonus": 99,
        "eeg_cashback": 0.1,
        "total_cost_runtime": 0,
        "total_cost_runtime_conventional": 0,
        "power_increase_rate": 3.9,
        "heating_increase_rate": 3.9,
        "car_increase_rate": 3.9,
        "inflation_rate": 1.00,
        "total_price_increase_rate": 0,
        "financing_rate": 4.89,
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
        "lightcloud_extra_price_per_kwh": 0.24,
        "heatcloud_extra_price_per_kwh": 0.27,
        "car_extra_price_per_kwh": 0.24,
        "maintainance_rate": 0.0605,
        "min_kwp": 0,
        "min_kwp_light": 0,
        "extra_stacks": 0,
        "extra_synergy_bonus": 0,
        "kwp_factor": 1.77,
        "kwp_heating_factor": 1.216,
        "kwp_car_factor": 1.186,
        "version1_investment_cost_per_kwp": 1390,
        "version2_investment_cost_storage": 10000,
        "version1_energy_factor": 0.75,
        "version2_energy_factor": 0.55,
        "version1_2_heating_decrase": 0.4,
        "version1_2_car_decrase": 0.4,

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
        "south_west_east": 874,
        "north_west_east": 788,
        "north": 603
    }
    for field in [
        "pv_kwp", "power_usage", "power_extra_usage", "heater_usage", "car_usage", "consumer_usage", "car_count",
        "power_increase_rate", "heating_increase_rate", "car_increase_rate", "inflation_rate", "financing_rate",
        "conventional_power_cost_per_kwh", "conventional_heat_cost_per_kwh"]:
        if data.get(field) not in [None, "", 0]:
            if field == "conventional_power_cost_per_kwh":
                calculated[field] = float(data.get(field)) / 100
            elif field == "conventional_heat_cost_per_kwh":
                calculated["conventional_heating_cost_per_kwh"] = float(data.get(field)) / 100
            else:
                calculated[field] = float(data.get(field))
    calculated["power_usage"] = calculated["power_usage"] + calculated["power_extra_usage"]
    calculated["power_extra_usage"] = 0
    calculated["total_usage"] = 0
    for field in ["power_usage", "power_extra_usage", "heater_usage","car_usage", "consumer_usage"]:
        if data.get(field) not in [None, "", 0]:
            calculated["total_usage"] = calculated["total_usage"] + calculated[field]
    calculated["total_light_usage"] = calculated["total_usage"] - calculated["heater_usage"] - calculated["car_usage"]
    size = 0
    if calculated["power_usage"] not in [None, "", 0, "0"]:
        size = size + math.ceil(calculated["power_usage"] / 4200) * 4.2
    if calculated["heater_usage"] not in [None, "", 0, "0"]:
        size = size + math.ceil(calculated["heater_usage"] / 9000) * 4.2
    if calculated["car_usage"] not in [None, "", 0, "0"]:
        size = size + math.ceil(calculated["car_usage"] / 4200) * 4.2
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
        size = math.ceil(calculated["total_usage"] / 4200) * 4.2
    if calculated["heater_usage"] > 0:
        size = size + 4.2
    if size > 50.4:
        size = 50.4 + math.ceil((calculated["total_usage"] - 50400) / 2 / 4200) * 4.2
        calculated["autocracy_rate"] = 64
    calculated["min_kwp"] = calculated["total_usage"] * calculated["kwp_factor"] / 1000
    if calculated["heater_usage"] > 0:
        calculated["min_kwp"] = calculated["min_kwp"] * calculated["kwp_heating_factor"]
    if calculated["car_usage"] > 0:
        calculated["min_kwp"] = calculated["min_kwp"] * calculated["kwp_car_factor"]
    calculated["min_kwp_light"] = calculated["min_kwp"]
    if calculated["min_kwp"] < calculated["pv_kwp"]:
        calculated["max_kwp"] = calculated["min_kwp"]
        calculated["kwp_extra"] = calculated["pv_kwp"] - calculated["max_kwp"]
        percent_kwp = calculated["min_kwp"] / calculated["pv_kwp"]
        calculated["autocracy_rate"] = math.floor(calculated["autocracy_rate"] + (100 - calculated["autocracy_rate"]) * percent_kwp * 0.06)
    else:
        calculated["max_kwp"] = calculated["pv_kwp"]
        calculated["kwp_extra"] = calculated["max_kwp"] - calculated["min_kwp"]
        #percent_kwp = calculated["pv_kwp"] / calculated["min_kwp"]
        #calculated["autocracy_rate"] = math.floor(calculated["autocracy_rate"] * (1.25*percent_kwp**3 - 3.3*percent_kwp**2 + 3.05*percent_kwp))
        calculated["autocracy_rate"] = calculated["autocracy_rate"] + calculated["autocracy_missing_kwp_nerf"] * calculated["kwp_extra"]
    calculated["min_storage_size"] = size
    calculated["storage_size"] = size
    if data.get("overwrite_storage_size") not in [None, 0, ""]:
        calculated["storage_size"] = float(data.get("overwrite_storage_size"))
    calculated["extra_stacks"] = math.floor((calculated["storage_size"] - calculated["min_storage_size"]) / 4.2)

    if calculated["storage_size"] > calculated["min_storage_size"]:
        calculated["autocracy_rate"] = calculated["autocracy_rate"] + calculated["synergy_extra_storage_stack_autocracy_bonus"] + (calculated["extra_stacks"] - 1) * calculated["synergy_extra_additional_storage_stack_autocracy_bonus"]
        calculated["extra_synergy_bonus"] = calculated["extra_synergy_bonus"] - (calculated["synergy_extra_storage_stack_cash_bonus"] + (calculated["extra_stacks"] - 1) * calculated["synergy_extra_additional_storage_stack_cash_bonus"])
    if calculated["storage_size"] < calculated["min_storage_size"]:
        calculated["autocracy_rate"] = calculated["autocracy_rate"] - calculated["synergy_first_missing_storage_stack_autocracy_nerf"] - (-calculated["extra_stacks"] - 1) * calculated["synergy_missing_storage_stack_autocracy_nerf"]
        calculated["extra_synergy_bonus"] = calculated["extra_synergy_bonus"] - (calculated["synergy_first_missing_storage_stack_cash_nerf"] + (calculated["extra_stacks"] - 1) * calculated["synergy_missing_storage_stack_cash_nerf"])
    if calculated["autocracy_rate"] > calculated["max_autocracy_rate"]:
        calculated["autocracy_rate"] = calculated["max_autocracy_rate"]
    if data.get("autocracy_rate") not in [None, "", 0] and data.get("synergy_autarkie_overwrite") not in [None, "", 0]:
        calculated["autocracy_rate"] = float(data.get("autocracy_rate"))
        print("asd", calculated["autocracy_rate"])
    calculated["power_total_increase_rate"] = calculated["inflation_rate"] + calculated["power_increase_rate"]
    calculated["heating_total_increase_rate"] = calculated["inflation_rate"] + calculated["heating_increase_rate"]
    calculated["car_total_increase_rate"] = calculated["inflation_rate"] + calculated["car_increase_rate"]
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
    calculated["synergy_bonus_monthly"] = -1 * calculated["direct_usage"] * calculated["synergy_bonus_factor"]
    if calculated["synergy_bonus_monthly"] > -12:
        calculated["synergy_bonus_monthly"] = -12
    calculated["synergy_bonus_monthly"] = calculated["synergy_bonus_monthly"] + calculated["extra_synergy_bonus"]
    if calculated["synergy_bonus_monthly"] > 0:
        calculated["synergy_bonus_monthly"] = 0
    if calculated["synergy_bonus_monthly"] < -calculated["synergy_hard_max_bonus"]:
        calculated["synergy_bonus_monthly"] = -calculated["synergy_hard_max_bonus"]
    if calculated["car_usage"] not in [None, "", 0, "0"] and calculated["car_count"] not in [None, "", 0, "0"]:
        calculated["synergy_bonus_monthly"] = calculated["synergy_bonus_monthly"] - (calculated["car_count"] * calculated["synergy_car_bonus"])
    calculated["synergy_bonus"] = calculated["synergy_bonus_monthly"] * 12
    calculated["net_usage"] = calculated["total_usage"] - calculated["direct_usage"]
    calculated["net_usage_cost"] = calculated["net_usage"] * calculated["lightcloud_extra_price_per_kwh"]
    calculated["net_usage_cost_monthly"] = calculated["net_usage_cost"] / 12
    calculated["feeding_amount"] = calculated["pv_production"] - calculated["direct_usage"]
    calculated["feeding_amount_bonus"] = -1 * calculated["feeding_amount"] * calculated["eeg_cashback"]
    calculated["feeding_amount_bonus_monthly"] = calculated["feeding_amount_bonus"] / 12
    calculated["synergy_monthly_today"] = calculated["net_usage_cost_monthly"] + calculated["synergy_bonus_monthly"] + calculated["feeding_amount_bonus_monthly"]
    calculated["conventional_cost_light_monthly_today"] = (calculated["total_light_usage"] * calculated["conventional_power_cost_per_kwh"]) / 12
    calculated["conventional_cost_heating_monthly_today"] = (calculated["heater_usage"] * calculated["conventional_heating_cost_per_kwh"]) / 12
    calculated["conventional_cost_car_monthly_today"] = (calculated["car_usage"] * calculated["conventional_car_cost_per_kwh"]) / 12
    calculated["conventional_cost_monthly_today"] = calculated["conventional_cost_light_monthly_today"] + calculated["conventional_cost_heating_monthly_today"] + calculated["conventional_cost_car_monthly_today"]
    for i in range(10, 35, 5):
        calculated[f"synergy_monthly_{i}years"] = calculated["net_usage_cost_monthly"] * (1 + calculated["power_increase_rate"] / 100) ** i + calculated["synergy_bonus_monthly"] + calculated["feeding_amount_bonus_monthly"]
        calculated[f"conventional_cost_light_monthly_{i}years"] = calculated["conventional_cost_light_monthly_today"] * (1 + calculated["power_total_increase_rate"] / 100) ** i
        calculated[f"conventional_cost_heating_monthly_{i}years"] = calculated["conventional_cost_heating_monthly_today"] * (1 + calculated["heating_total_increase_rate"] / 100) ** i
        calculated[f"conventional_cost_car_monthly_{i}years"] = calculated["conventional_cost_car_monthly_today"] * (1 + calculated["car_total_increase_rate"] / 100) ** i
        calculated[f"conventional_cost_monthly_{i}years"] = calculated[f"conventional_cost_light_monthly_{i}years"] + calculated[f"conventional_cost_heating_monthly_{i}years"] + calculated[f"conventional_cost_car_monthly_{i}years"]
    calculated["conventional_cost_light_total"] = 0
    calculated["conventional_cost_heating_total"] = 0
    calculated["conventional_cost_car_total"] = 0
    calculated["conventional_cost_total"] = 0
    calculated["synergy_total"] = 0
    for i in range(1, calculated["runtime"] + 1):
        calculated["synergy_total"] = calculated["synergy_total"] + (calculated["net_usage_cost_monthly"] * (1 + calculated["power_increase_rate"] / 100) ** i + calculated["synergy_bonus_monthly"] + calculated["feeding_amount_bonus_monthly"]) * 12
        calculated["conventional_cost_light_total"] = calculated["conventional_cost_light_total"] + (calculated["conventional_cost_light_monthly_today"] * (1 + calculated["power_total_increase_rate"] / 100) ** i) * 12
        calculated["conventional_cost_heating_total"] = calculated["conventional_cost_heating_total"] + (calculated["conventional_cost_heating_monthly_today"] * (1 + calculated["heating_total_increase_rate"] / 100) ** i) * 12
        calculated["conventional_cost_car_total"] = calculated["conventional_cost_car_total"] + (calculated["conventional_cost_car_monthly_today"] * (1 + calculated["car_total_increase_rate"] / 100) ** i) * 12
        calculated["conventional_cost_total"] = calculated["conventional_cost_light_total"] + calculated["conventional_cost_heating_total"] + calculated["conventional_cost_car_total"]
        if i in [10, 15, 20, 25, 30]:
            calculated[f"synergy_total_{i}years"] = calculated["synergy_total"]
            calculated[f"conventional_cost_total_{i}years"] = calculated["conventional_cost_total"]
            calculated[f"conventional_cost_monthly_avarage_{i}years"] = calculated["conventional_cost_total"] / i / 12
    calculated["version1"] = {
        "investment_cost": calculated["pv_kwp"] * calculated["version1_investment_cost_per_kwp"],
    }
    calculated["version2"] = {
        "investment_cost": calculated["pv_kwp"] * calculated["version1_investment_cost_per_kwp"] + calculated["version2_investment_cost_storage"],
    }
    if i in [10, 15, 20, 25, 30]:
        calculated["version1"][f"energy_cost_{i}years"] = calculated[f"conventional_cost_total_{i}years"] * calculated["version1_energy_factor"]
        calculated["version1"][f"total_cost_{i}years"] = calculated["version1"][f"energy_cost_{i}years"] + calculated["version1"]["investment_cost"]
        calculated["version1"][f"savings_{i}years"] = calculated[f"conventional_cost_total_{i}years"] - calculated["version1"][f"total_cost_{i}years"]
        calculated["version2"][f"energy_cost_{i}years"] = calculated[f"conventional_cost_total_{i}years"] * calculated["version2_energy_factor"]
        calculated["version2"][f"total_cost_{i}years"] = calculated["version2"][f"energy_cost_{i}years"] + calculated["version2"]["investment_cost"]
        calculated["version2"][f"savings_{i}years"] = calculated[f"conventional_cost_total_{i}years"] - calculated["version2"][f"total_cost_{i}years"]

    return calculated


def calculate_synergy_wi2(return_data):
    calculated = return_data["calculated"]
    if "total_net" not in return_data:
        print("asd", json.dumps(return_data, indent=2))
    calculated["maintainance_cost_total"] = return_data["total_net"] * calculated["maintainance_rate"]
    calculated["maintainance_cost_monthly"] = calculated["maintainance_cost_total"] / 10 / 12
    calculated["invenstment_cost_total"] = return_data["total_net"]
    calculated["invenstment_cost_monthly"] = return_data["total_net"] / 20 / 12
    if "loan_calculation" in return_data:
        calculated["invenstment_cost_total"] = return_data["loan_calculation"]["total_cost"]
        calculated["invenstment_cost_monthly"] = return_data["loan_calculation"]["monthly_payment"]

    calculated["synergy_monthly_today_total"] = calculated["synergy_monthly_today"] + calculated["invenstment_cost_monthly"]
    for i in range(10, 35, 5):
        if i <= 20:
            calculated[f"synergy_monthly_{i}years_total"] = calculated[f"synergy_monthly_{i}years"] + calculated["invenstment_cost_monthly"]
            calculated[f"synergy_total_investment_cost_{i}years"] = calculated[f"synergy_total_{i}years"] + i * 12 * calculated["invenstment_cost_monthly"]
        else:
            calculated[f"synergy_monthly_{i}years_total"] = calculated[f"synergy_monthly_{i}years"] + calculated["maintainance_cost_monthly"]
            calculated[f"synergy_total_investment_cost_{i}years"] = calculated[f"synergy_total_{i}years"] + calculated["invenstment_cost_total"] + (i - 20) * 12 * calculated["maintainance_cost_monthly"]
        calculated[f"synergy_monthly_avarage_{i}years"] = calculated[f"synergy_total_investment_cost_{i}years"] / i / 12
        calculated[f"synergy_total_savings_{i}years"] = calculated[f"conventional_cost_total_{i}years"] - calculated[f"synergy_total_investment_cost_{i}years"]

    calculated["graph_data"] = {
        "max": math.ceil(calculated["conventional_cost_total_30years"] / 20000) * 20000,
    }
    calculated["graph_data"]["conventional_cost_percent"] = calculated["conventional_cost_total_30years"] / calculated["graph_data"]["max"]
    calculated["graph_data"]["synergy_investment_percent"] = calculated["invenstment_cost_total"] / calculated["graph_data"]["max"]
    calculated["graph_data"]["synergy_total_cost_percent"] = calculated["synergy_total_investment_cost_30years"] / calculated["graph_data"]["max"]
    calculated["graph_data"]["version2_investment_percent"] = calculated["version2"]["investment_cost"] / calculated["graph_data"]["max"]
    calculated["graph_data"]["version2_total_cost_percent"] = calculated["version2"]["total_cost_30years"]  / calculated["graph_data"]["max"]
    calculated["graph_data"]["version1_investment_percent"] = calculated["version1"]["investment_cost"] / calculated["graph_data"]["max"]
    calculated["graph_data"]["version1_total_cost_percent"] = calculated["version1"]["total_cost_30years"] / calculated["graph_data"]["max"]
    return return_data["calculated"]


def generate_synergy_pdf(lead_id, data, only_pages=None):
    config_general = get_settings(section="general")
    if data is not None:
        data["base_url"] = config_general["base_url"]
        if "datetime" not in data:
            data["datetime"] = datetime.datetime.now()
        # base_pdf = PdfFileReader(io.BytesIO(get_file_content_cached(7476459)))  # https://keso.bitrix24.de/disk/downloadFile/7476459/?&ncc=1&filename=Synergie+360+WI.pdf
        # base_pdf = PdfFileReader(io.BytesIO(get_file_content_cached(7800623)))  # https://keso.bitrix24.de/disk/downloadFile/7800623/?&ncc=1&filename=Broschu%CC%88re+03052023.pdf
        # base_pdf = PdfFileReader(io.BytesIO(get_file_content_cached(8149181)))  # https://keso.bitrix24.de/disk/downloadFile/8149181/?&ncc=1&filename=Broschu%CC%88re+05062023.pdf
        base_pdf = PdfFileReader(io.BytesIO(get_file_content_cached(8430171))) # https://keso.bitrix24.de/disk/downloadFile/8430171/?&ncc=1&filename=Brosch%C3%BCre+30062023+%281%29.pdf

        hide_pages = [16, 17, 18, 19, 20, 21, 24]
        if data.get("data").get("module_kwp").get("label") == "PV-Modul Amerisolar 380 Watt Black":
            hide_pages.remove(16)
        if data.get("data").get("module_kwp").get("label") == "PV Modul SENEC.SOLAR 380 Watt BLACK":
            hide_pages.remove(17)
        if data.get("data").get("module_kwp").get("label") == "SENEC 410 Watt Hochleistungsmodul":
            hide_pages.remove(18)
        if data.get("data").get("module_kwp").get("label") == "BLACKSTAR SOLID FRAMED GLASS/GLASS 420 Watt":
            hide_pages.remove(19)
        if data.get("data").get("module_kwp").get("label") == "Bifazial Glas/Glas 410 Watt Black PV Modul.":
            hide_pages.remove(20)
        if "solaredge" in data.get("data").get("extra_options"):
            hide_pages.remove(21)
        if "wallbox" in data.get("data").get("extra_options") and data.get("data").get("extra_options_wallbox_variant") in ["senec-pro-11kW", "senec-pro-22kW"]:
            hide_pages.remove(24)
        print(hide_pages)
        total_pages = base_pdf.getNumPages() - len(hide_pages)
        content = render_template(
            "quote_calculator/generator/synergy_wi/index.html",
            base_url=config_general["base_url"],
            lead_id=lead_id,
            data=data,
            hide_pages=hide_pages,
            total_pages=total_pages
        )
        data["datetime"] = str(data["datetime"])
        overlay_pdf = PdfFileReader(io.BytesIO(gotenberg_pdf(
            content,
            margins=["0", "0", "0", "0"],
            landscape=True)))
        offset = 0
        pdf = PdfFileWriter()
        for i in range(0, total_pages):
            if only_pages is not None and i not in only_pages:
                continue
            if i + offset in hide_pages:
                offset = offset + 1
                while i + offset in hide_pages:
                    offset = offset + 1
            print(base_pdf.getNumPages(), i, offset, i+offset+1)
            if i in [11, 12, 13, 14, total_pages - 3, total_pages - 2, total_pages - 1]:
                page = overlay_pdf.getPage(i)
            else:
                page = overlay_pdf.getPage(i)
                if i + offset < base_pdf.getNumPages():
                    page.mergePage(base_pdf.getPage(i + offset))
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