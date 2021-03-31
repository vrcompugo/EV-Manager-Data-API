import math
from functools import reduce
from flask import render_template

from app.models import OfferV2
from app.utils.jinja_filters import numberformat
from app.modules.settings.settings_services import get_one_item as get_settings
from app.modules.auth.auth_services import get_logged_in_user

from app.modules.offer.services.offer_generation._utils import base_offer_data, add_item_to_offer, add_optional_item_to_offer


def calculate_cloud(data):
    settings = get_settings("pv-settings")
    if settings is None:
        return None
    user = {"id": 1}
    try:
        user = get_logged_in_user()
    except Exception as e:
        pass
    user_id_for_prices = user["id"]
    if user_id_for_prices not in [113, 119, 120, 121, 123]:
        user_id_for_prices = 1
    if data.get("assigned_user") is not None:
        if 330 in data["assigned_user"]["UF_DEPARTMENT"] or "330" in data["assigned_user"]["UF_DEPARTMENT"]:
            user = {"id": 120, "name": "bsh"}
            user_id_for_prices = 120
    result = {
        "lightcloud_extra_price_per_kwh": settings["data"]["cloud_settings"]["lightcloud_extra_price_per_kwh"],
        "heatcloud_extra_price_per_kwh": settings["data"]["cloud_settings"]["heatcloud_extra_price_per_kwh"],
        "ecloud_extra_price_per_kwh": settings["data"]["cloud_settings"]["ecloud_extra_price_per_kwh"],
        "consumercloud_extra_price_per_kwh": settings["data"]["cloud_settings"]["lightcloud_extra_price_per_kwh"],
        "errors": [],
        "invalid_form": False,
        "kwp_extra": 0,
        "pv_kwp": 0,
        "min_kwp": 0,
        "min_kwp_light": 0,
        "min_kwp_heatcloud": 0,
        "min_kwp_ecloud": 0,
        "min_kwp_emove": 0,
        "min_kwp_consumer": 0,
        "storage_size": 0,
        "cloud_price_extra": 0,
        "cloud_price": 0,
        "cloud_price_incl_refund": 0,
        "cloud_price_light": 0,
        "cloud_price_light_incl_refund": 0,
        "cloud_price_heatcloud": 0,
        "cloud_price_heatcloud_incl_refund": 0,
        "cloud_price_ecloud": 0,
        "cloud_price_ecloud_incl_refund": 0,
        "cloud_price_emove": 0,
        "cloud_price_emove_incl_refund": 0,
        "cloud_price_consumer": 0,
        "cloud_price_consumer_incl_refund": 0,
        "user_one_time_cost": 0,
        "power_usage": 0,
        "heater_usage": 0,
        "ecloud_usage": 0,
        "consumer_usage": 0,
        "conventional_price_light": 0,
        "conventional_price_heatcloud": 0,
        "conventional_price_ecloud": 0,
        "conventional_price_consumer": 0
    }
    if data is not None and "conventional_power_cost_per_kwh" in data and data["conventional_power_cost_per_kwh"] is not None and data["conventional_power_cost_per_kwh"] != "":
        data["conventional_power_cost_per_kwh"] = float(data["conventional_power_cost_per_kwh"])
    else:
        data["conventional_power_cost_per_kwh"] = 31
    result["conventional_power_cost_per_kwh"] = data["conventional_power_cost_per_kwh"]
    pv_efficiancy_faktor = None
    if "name" in user and user["name"].lower() == "bsh":
        settings["data"]["cloud_settings"]["ecloud_to_kwp_factor"] = 2405
        if "pv_efficiancy" in data and data["pv_efficiancy"] is not None and data["pv_efficiancy"] != "":
            pv_efficiancy_faktor = int(data["pv_efficiancy"]) / 950
    if "pv_kwp" in data and data["pv_kwp"] is not None and data["pv_kwp"] != "":
        data["pv_kwp"] = float(data["pv_kwp"])
        result["pv_kwp"] = data["pv_kwp"]
    else:
        data["pv_kwp"] = 0
    if data["pv_kwp"] > 99 and str(user["id"]) != "13" and str(user["id"]) != "107":
        return None
    if pv_efficiancy_faktor is None:
        direction_factor_kwp = 1
        direction_factor_production = 1
        if "roof_direction" in data:
            direction_factor_kwp, direction_factor_production = factors_by_direction(data["roof_direction"])
            if "price_guarantee" in data and data["price_guarantee"] == "2_years":
                if data["roof_direction"] == "north":
                    direction_factor_kwp = 1.35
                    direction_factor_production = 0.65

        if "roofs" in data and data["roofs"] is not None:
            total_roof_space = 0
            for roof in data["roofs"]:
                if "sqm" in roof and roof["sqm"] is not None and roof["sqm"] != "":
                    total_roof_space = total_roof_space + float(roof["sqm"])
            if total_roof_space == 0:
                direction_factor_kwp, direction_factor_production = factors_by_direction("west_east")
                if len(data["roofs"]) > 0 and "direction" in data["roofs"][0]:
                    direction_factor_kwp, direction_factor_production = factors_by_direction(data["roofs"][0]["direction"])
            else:
                direction_factor_kwp = 0
                direction_factor_production = 0
                for roof in data["roofs"]:
                    if "sqm" in roof and roof["sqm"] is not None and roof["sqm"] != "":
                        x, y = factors_by_direction(roof["direction"])
                        direction_factor_kwp = direction_factor_kwp + (float(roof["sqm"]) / total_roof_space) * x
                        direction_factor_production = direction_factor_kwp + (float(roof["sqm"]) / total_roof_space) * y
    else:
        direction_factor_kwp = 1 / pv_efficiancy_faktor
        direction_factor_production = pv_efficiancy_faktor
    if "power_usage" in data and data["power_usage"] != "" and data["power_usage"] != "0" and data["power_usage"] != 0:
        data["power_usage"] = int(data["power_usage"])
        power_to_kwp_factor = settings["data"]["cloud_settings"]["power_to_kwp_factor"]
        if 0 < data["power_usage"] <= 7000:
            power_to_kwp_factor = 1.6
        if 7000 < data["power_usage"] <= 25000:
            power_to_kwp_factor = 1.78
        if 25000 < data["power_usage"] <= 52000:
            power_to_kwp_factor = 1.89
        if 52000 < data["power_usage"] < 300000:
            power_to_kwp_factor = 2.07
        if 300000 <= data["power_usage"] < 750000:
            power_to_kwp_factor = 2.55
        if 750000 <= data["power_usage"]:
            power_to_kwp_factor = 3.37
        if "price_guarantee" in data and data["price_guarantee"] == "2_years":
            if 0 < data["power_usage"] <= 7000:
                power_to_kwp_factor = 1.4
            if 7000 < data["power_usage"] <= 25000:
                power_to_kwp_factor = 1.55
            if 25000 < data["power_usage"] < 52000:
                power_to_kwp_factor = 1.87
            if 52000 < data["power_usage"] <= 300000:
                power_to_kwp_factor = 2.07
            if 300000 <= data["power_usage"] < 750000:
                power_to_kwp_factor = 2.55
            if 750000 <= data["power_usage"]:
                power_to_kwp_factor = 3.37
        if "name" in user and user["name"].lower() in ["aev", "eeg"]:
            power_to_kwp_factor = power_to_kwp_factor * 1.34
        result["power_usage"] = data["power_usage"]
        result["min_kwp_light"] = data["power_usage"] * power_to_kwp_factor * direction_factor_kwp / 1000
        result["storage_size"] = round((data["power_usage"] / 500)) * 500 / 1000
        result["storage_usage"] = data["power_usage"]
        if data["pv_kwp"] > 0:
            storage_usage_by_kwp = data["pv_kwp"] * 1000 / power_to_kwp_factor / direction_factor_kwp
            if storage_usage_by_kwp < result["storage_usage"]:
                result["storage_usage"] = storage_usage_by_kwp
        result["min_storage_size"] = result["storage_size"]
        if "name" in user and user["name"].lower() == "bsh":
            result["storage_size"] = math.ceil(result["storage_usage"] / 2500) * 2.5
            if 7501 <= result["storage_usage"] <= 11500:
                result["storage_size"] = 10
            if 11500 < result["storage_usage"]:
                result["storage_size"] = math.ceil(result["storage_usage"] / 5000) * 5
            if result["storage_size"] < 5:
                result["storage_size"] = 5
            if result["storage_size"] > 30:
                result["storage_size"] = 30
            result["min_storage_size"] = result["storage_size"]
            if "min_storage_size_overwrite" in data and data["min_storage_size_overwrite"] != "":
                if int(data["min_storage_size_overwrite"]) > result["storage_size"]:
                    result["storage_size"] = data["min_storage_size_overwrite"]

        result["cloud_price_light"] = result["cloud_price_light"] + list(filter(
            lambda item: item['from'] <= data["power_usage"] and data["power_usage"] <= item['to'],
            settings["data"]["cloud_settings"]["cloud_user_prices"][str(user_id_for_prices)]
        ))[0]["value"]
        print(data["price_guarantee"])
        if "price_guarantee" in data and data["price_guarantee"] == "2_years":
            if 0 < data["power_usage"] <= 5000:
                result["cloud_price_light"] = 29
            if 5000 < data["power_usage"] <= 7000:
                result["cloud_price_light"] = 29
            if 7000 < data["power_usage"] <= 9000:
                result["cloud_price_light"] = 39
            if 9000 < data["power_usage"] <= 12000:
                result["cloud_price_light"] = 49
            if 12000 < data["power_usage"] <= 14000:
                result["cloud_price_light"] = 69
            if 14000 < data["power_usage"] <= 20000:
                result["cloud_price_light"] = 99
            if "name" in user and user["name"].lower() == "bsh":
                result["cloud_price_light"] = data["power_usage"] * 0.4755 / 10 / 12
        result["conventional_price_light"] = (data["power_usage"] * result["lightcloud_extra_price_per_kwh"]) / 12

        result["conventional_price_light"] = (data["power_usage"] * data["conventional_power_cost_per_kwh"] / 100) / 12

    if "heater_usage" in data and data["heater_usage"] != "" and data["heater_usage"] != "0" and data["heater_usage"] != 0:
        data["heater_usage"] = int(data["heater_usage"])
        result["heater_usage"] = data["heater_usage"]
        heater_to_kwp_factor = list(filter(
            lambda item: item['from'] <= data["heater_usage"] and data["heater_usage"] <= item['to'],
            settings["data"]["cloud_settings"]["heater_to_kwp_factor"]
        ))[0]["value"]
        result["cloud_price_heatcloud"] = list(filter(
            lambda item: item['from'] <= data["heater_usage"] and data["heater_usage"] <= item['to'],
            settings["data"]["cloud_settings"]["cloud_user_heater_prices"][str(user_id_for_prices)]
        ))[0]["value"]
        result["min_kwp_heatcloud"] = data["heater_usage"] * heater_to_kwp_factor * direction_factor_kwp / 1000
        result["conventional_price_heatcloud"] = (data["heater_usage"] * settings["data"]["cloud_settings"]["heatcloud_conventional_price_per_kwh"]) / 12
        if data is not None and "conventional_heat_cost_per_kwh" in data and data["conventional_heat_cost_per_kwh"] is not None and data["conventional_heat_cost_per_kwh"] != "":
            data["conventional_heat_cost_per_kwh"] = float(data["conventional_heat_cost_per_kwh"])
            result["conventional_price_heatcloud"] = (data["heater_usage"] * data["conventional_heat_cost_per_kwh"] / 100) / 12

    if "ecloud_usage" in data and data["ecloud_usage"] != "" and data["ecloud_usage"] != "0" and data["ecloud_usage"] != 0:
        data["ecloud_usage"] = int(data["ecloud_usage"])
        result["ecloud_usage"] = data["ecloud_usage"]
        if type(settings["data"]["cloud_settings"]["cloud_user_ecloud_prices"][str(user_id_for_prices)]) is list:
            result["cloud_price_ecloud"] = list(filter(
                lambda item: item['from'] <= data["ecloud_usage"] and data["ecloud_usage"] <= item['to'],
                settings["data"]["cloud_settings"]["cloud_user_ecloud_prices"][str(user_id_for_prices)]
            ))[0]["value"]
        else:
            result["cloud_price_ecloud"] = settings["data"]["cloud_settings"]["cloud_user_ecloud_prices"][str(user_id_for_prices)]
        result["min_kwp_ecloud"] = data["ecloud_usage"] / settings["data"]["cloud_settings"]["ecloud_to_kwp_factor"]
        settings["data"]["cloud_settings"]["ecloud_conventional_price_per_kwh"]
        result["conventional_price_ecloud"] = (data["ecloud_usage"] * settings["data"]["cloud_settings"]["ecloud_conventional_price_per_kwh"]) / 12
        if data is not None and "conventional_gas_cost_per_kwh" in data and data["conventional_gas_cost_per_kwh"] is not None and data["conventional_gas_cost_per_kwh"] != "":
            data["conventional_gas_cost_per_kwh"] = float(data["conventional_gas_cost_per_kwh"])
            result["conventional_price_ecloud"] = (data["ecloud_usage"] * data["conventional_gas_cost_per_kwh"] / 100) / 12
    if "consumers" in data:
        consumer_usage = 0
        for consumer in data["consumers"]:
            consumer_usage = consumer_usage + int(consumer["usage"])
            consumer_price = list(filter(
                lambda item: item['from'] <= int(consumer["usage"]) and int(consumer["usage"]) <= item['to'],
                settings["data"]["cloud_settings"]["cloud_user_consumer_prices"][str(user_id_for_prices)]
            ))
            if len(consumer_price) > 0:
                result["cloud_price_consumer"] = result["cloud_price_consumer"] + consumer_price[0]["value"]
        result["consumer_usage"] = consumer_usage
        result["min_kwp_consumer"] = (consumer_usage * settings["data"]["cloud_settings"]["consumer_to_kwp_factor"] * direction_factor_kwp) / 1000
        result["conventional_price_consumer"] = (
            (
                settings["data"]["wi_settings"]["conventional_base_cost_per_year"] * len(data["consumers"])
                + result["consumer_usage"] * result["consumercloud_extra_price_per_kwh"]
            ) / 12
        )
        if "conventional_power_cost_per_kwh" in data and data["conventional_power_cost_per_kwh"] != "":
            result["conventional_price_consumer"] = (
                (
                    settings["data"]["wi_settings"]["conventional_base_cost_per_year"] * len(data["consumers"])
                    + result["consumer_usage"] * data["conventional_power_cost_per_kwh"] / 100
                ) / 12
            )

    result["conventional_price_emove"] = 0
    result["emove_usage"] = 0
    if "emove_tarif" in data:
        if data["emove_tarif"] in settings["data"]["cloud_settings"]["cloud_emove"]:
            result["min_kwp_emove"] = settings["data"]["cloud_settings"]["cloud_emove"][data["emove_tarif"]]["kwp"]
            result["cloud_price_emove"] = settings["data"]["cloud_settings"]["cloud_emove"][data["emove_tarif"]]["price"]
            if data["emove_tarif"] == "emove.drive I":
                result["conventional_price_emove"] = 8000 / 100 * 7 * 1.19 / 12
                result["emove_usage"] = 1500
            if data["emove_tarif"] == "emove.drive II":
                result["conventional_price_emove"] = 12000 / 100 * 7 * 1.19 / 12
                result["emove_usage"] = 2000
            if data["emove_tarif"] == "emove.drive III":
                result["conventional_price_emove"] = 20000 / 100 * 7 * 1.19 / 12
                result["emove_usage"] = 5000
            if data["emove_tarif"] == "emove.drive ALL":
                result["conventional_price_emove"] = 25000 / 100 * 7 * 1.19 / 12
                result["emove_usage"] = 8500

    if "price_guarantee" in data:
        if str(user_id_for_prices) in settings["data"]["cloud_settings"]["cloud_guarantee"]:
            if data["price_guarantee"] in settings["data"]["cloud_settings"]["cloud_guarantee"][str(user_id_for_prices)]:
                result["user_one_time_cost"] = result["user_one_time_cost"] + settings["data"]["cloud_settings"]["cloud_guarantee"][str(user_id_for_prices)][data["price_guarantee"]]["price"]

    if result["power_usage"] <= 0:
        result["invalid_form"] = True
        result["errors"].append("Lichtstrom muss immer bestellt werden")

    if 0 < data["pv_kwp"] < result["min_kwp_emove"]:
        result["invalid_form"] = True
        result["errors"].append("eMove Tarife sind nür möglich sofern diese mindestens durch die Anlage abgedeckt sind.")

    result["min_kwp"] = (result["min_kwp_light"]
                         + result["min_kwp_heatcloud"]
                         + result["min_kwp_ecloud"]
                         + result["min_kwp_consumer"]
                         + result["min_kwp_emove"])
    cloud_total = result["cloud_price_light"] + result["cloud_price_heatcloud"] + result["cloud_price_ecloud"] + result["cloud_price_consumer"] + result["cloud_price_emove"]
    if cloud_total > 83.3333333333:
        cloud_total_small = cloud_total - 83.3333333333
        result["min_zero_kwp"] = result["min_kwp"] + 10 + cloud_total_small / ((1000 * 0.08) / 12)
    else:
        result["min_zero_kwp"] = result["min_kwp"] + cloud_total / ((1000 * 0.1) / 12)
    result["cloud_price_light_incl_refund"] = result["cloud_price_light"]
    result["cloud_price_heatcloud_incl_refund"] = result["cloud_price_heatcloud"]
    result["cloud_price_ecloud_incl_refund"] = result["cloud_price_ecloud"]
    result["cloud_price_consumer_incl_refund"] = result["cloud_price_consumer"]
    result["cloud_price_emove_incl_refund"] = result["cloud_price_emove"]

    result["cloud_price"] = (result["cloud_price_light"]
                             + result["cloud_price_heatcloud"]
                             + result["cloud_price_ecloud"]
                             + result["cloud_price_consumer"]
                             + result["cloud_price_emove"])
    if data["pv_kwp"] > 0:
        result["kwp_extra"] = data["pv_kwp"] - result["min_kwp"]
        max_kwp = (
            result["min_kwp_light"]
            + result["min_kwp_heatcloud"]
            + result["min_kwp_ecloud"]
            + result["min_kwp_consumer"])
        extra_kwh_ratio = 1 - (data["pv_kwp"] - result["min_kwp_emove"]) / max_kwp
        if result["kwp_extra"] >= 0:
            if user_id_for_prices != 1:
                result["cloud_price_extra"] = -1 * result["kwp_extra"] * 8.33
                if result["kwp_extra"] > 10:
                    small_extra = result["kwp_extra"] - 10
                    result["cloud_price_extra"] = -(small_extra * 8.33 + (result["kwp_extra"] - small_extra) * 6.666666667)
            else:
                if result["kwp_extra"] > 10:
                    small_extra = result["kwp_extra"] - 10
                    result["cloud_price_extra"] = -(10 * 1000 * 0.1 + small_extra * 1000 * 0.08) / 12
                else:
                    result["cloud_price_extra"] = -(result["kwp_extra"] * 1000 * 0.1) / 12
                if -4 < (result["cloud_price"] + result["cloud_price_extra"]) < 0:
                    result["cloud_price_extra"] = -result["cloud_price"]
                if -4 < result["cloud_price_extra"] < 0:
                    result["cloud_price_extra"] = 0
            result["cloud_price_extra_light"] = (result["min_kwp_light"] / max_kwp) * result["cloud_price_extra"]
            result["cloud_price_extra_heatcloud"] = (result["min_kwp_heatcloud"] / max_kwp) * result["cloud_price_extra"]
            result["cloud_price_extra_ecloud"] = (result["min_kwp_ecloud"] / max_kwp) * result["cloud_price_extra"]
            result["cloud_price_extra_consumer"] = (result["min_kwp_consumer"] / max_kwp) * result["cloud_price_extra"]
        if result["kwp_extra"] < 0:
            result["cloud_price_extra"] = -1 * result["kwp_extra"] * 10.97
            if "price_guarantee" in data and data["price_guarantee"] == "2_years":
                result["cloud_price_extra"] = -1 * result["kwp_extra"] * 8.49
            result["cloud_price_extra_light"] = (result["min_kwp_light"] / max_kwp) * result["cloud_price_extra"]
            result["cloud_price_extra_heatcloud"] = (result["min_kwp_heatcloud"] / max_kwp) * result["cloud_price_extra"]
            result["cloud_price_extra_ecloud"] = (result["min_kwp_ecloud"] / max_kwp) * result["cloud_price_extra"]
            result["cloud_price_extra_consumer"] = (result["min_kwp_consumer"] / max_kwp) * result["cloud_price_extra"]
            result["cloud_price_extra_emove"] = 0
            if "name" in user and user["name"].lower() == "bsh":
                max_shared_kwp = result["min_kwp_light"] + result["min_kwp_heatcloud"] + result["min_kwp_emove"]
                if data["pv_kwp"] < max_shared_kwp:
                    rest_kwp = max_shared_kwp - data["pv_kwp"]
                    rest_kwp_light = result["min_kwp_light"] / max_shared_kwp * rest_kwp
                    rest_kwp_heatcloud = result["min_kwp_heatcloud"] / max_shared_kwp * rest_kwp
                    rest_kwp_emove = result["min_kwp_emove"] / max_shared_kwp * rest_kwp
                    result["cloud_price_extra_light"] = ((rest_kwp_light / result["min_kwp_light"]) * result["power_usage"] * result["lightcloud_extra_price_per_kwh"]) / 12
                    result["cloud_price_extra_heatcloud"] = 0
                    if result["min_kwp_heatcloud"] > 0:
                        result["cloud_price_extra_heatcloud"] = ((rest_kwp_heatcloud / result["min_kwp_heatcloud"]) * result["heater_usage"] * result["heatcloud_extra_price_per_kwh"]) / 12
                    result["cloud_price_extra_emove"] = 0
                    if result["min_kwp_emove"] > 0:
                        result["cloud_price_extra_emove"] = ((rest_kwp_emove / result["min_kwp_emove"]) * result["emove_usage"] * result["lightcloud_extra_price_per_kwh"]) / 12
                    rest_kwp = 0
                else:
                    result["cloud_price_extra_light"] = 0
                    result["cloud_price_extra_heatcloud"] = 0
                    result["cloud_price_extra_emove"] = 0
                    rest_kwp = data["pv_kwp"] - max_shared_kwp
                if rest_kwp >= result["min_kwp_ecloud"]:
                    result["cloud_price_extra_ecloud"] = 0
                    rest_kwp = rest_kwp - result["min_kwp_ecloud"]
                else:
                    result["cloud_price_extra_ecloud"] = ((1 - rest_kwp / result["min_kwp_ecloud"]) * result["ecloud_usage"] * result["ecloud_extra_price_per_kwh"]) / 12
                    rest_kwp = 0

                if rest_kwp >= result["min_kwp_consumer"]:
                    result["cloud_price_extra_consumer"] = 0
                    rest_kwp = rest_kwp - result["min_kwp_consumer"]
                else:
                    result["cloud_price_extra_consumer"] = ((1 - rest_kwp / result["min_kwp_consumer"]) * result["consumer_usage"] * result["lightcloud_extra_price_per_kwh"]) / 12
                    rest_kwp = 0

            result["cloud_price_extra"] = (
                result["cloud_price_extra_light"]
                + result["cloud_price_extra_heatcloud"]
                + result["cloud_price_extra_ecloud"]
                + result["cloud_price_extra_consumer"]
                + result["cloud_price_extra_emove"]
            )
        result["cloud_price_light_incl_refund"] = result["cloud_price_light"] + result["cloud_price_extra_light"]
        result["cloud_price_heatcloud_incl_refund"] = result["cloud_price_heatcloud"] + result["cloud_price_extra_heatcloud"]
        result["cloud_price_ecloud_incl_refund"] = result["cloud_price_ecloud"] + result["cloud_price_extra_ecloud"]
        result["cloud_price_consumer_incl_refund"] = result["cloud_price_consumer"] + result["cloud_price_extra_consumer"]

    result["cloud_price"] = (result["cloud_price_light"]
                             + result["cloud_price_heatcloud"]
                             + result["cloud_price_ecloud"]
                             + result["cloud_price_consumer"]
                             + result["cloud_price_emove"])

    result["conventional_price"] = (result["conventional_price_light"]
                                    + result["conventional_price_consumer"]
                                    + result["conventional_price_heatcloud"]
                                    + result["conventional_price_ecloud"]
                                    + result["conventional_price_emove"])

    result["max_kwp"] = result["min_kwp"] + result["kwp_extra"]
    result["cloud_price_incl_refund"] = result["cloud_price"] + result["cloud_price_extra"]

    if "cloud_price_wish" in data and data["cloud_price_wish"] != "" and data["cloud_price_wish"] != "0" and data["cloud_price_wish"] != 0:
        if result["cloud_price_incl_refund"] > float(data["cloud_price_wish"]) > 0 and "price_guarantee" in data and data["price_guarantee"] == "2_years":
            price_diff = result["cloud_price_incl_refund"] - float(data["cloud_price_wish"])
            result["user_one_time_cost"] = result["user_one_time_cost"] + (result["cloud_price_incl_refund"] - float(data["cloud_price_wish"])) * 24

    return result


def factors_by_direction(direction):
    direction_factor_kwp = 1
    direction_factor_production = 1
    if direction == "north":
        direction_factor_kwp = 1.30
        direction_factor_production = 0.65
    if direction == "west_east":
        direction_factor_kwp = 1.05
        direction_factor_production = 0.8
    if direction == "south_west_east":
        direction_factor_kwp = 1.02
        direction_factor_production = 0.92
    return direction_factor_kwp, direction_factor_production


def get_cloud_products(data=None, offer=None):
    settings = get_settings("pv-settings")
    if settings is None:
        return None
    tax_rate = 19
    offer_data = {}
    wish_price = False
    pv_production = (
        "<b>PV Erzeugung</b><br>\n"
        + f"PV-Anlage mit mindestens: {numberformat(float(data['calculated']['min_kwp']), digits=2)} kWp<br>\n"
        + f"Speicher-Anlage mit mindestens: {numberformat(float(data['calculated']['storage_size']), digits=2)} kWh<br>\n"
    )
    if "pv_kwp" in data['data'] and data['data']["pv_kwp"] > 0:
        pv_production = (
            "<b>PV Erzeugung</b><br>\n"
            + f"PV-Anlage mindestens zu verbauen: {numberformat(float(data['calculated']['min_kwp']), digits=2)} kWp<br>\n"
            + f"PV-Anlage wird verbaut: {numberformat(float(data['data']['pv_kwp']), digits=3)} kWp<br>\n"
            + f"Speicher-Anlage mit mindestens: {numberformat(float(data['calculated']['storage_size']), digits=2)} kWh<br>\n"
        )
    if offer is not None:
        pv_production = (
            "<b>PV Erzeugung</b><br>\n"
            + f"Zählernummer: {offer.survey.data['current_counter_number']}<br>\n"
            + f"PV-Anlage laut Angebot: PV-{offer.id}<br>\n"
            + f"{offer.survey.data['street']} {offer.survey.data['zip']} {offer.survey.data['city']}<br>\n"
        )
    cloud_price = data["calculated"]["cloud_price_light"]
    if "cloud_price_wish" in data["data"] and data["data"]["cloud_price_wish"] != "" and 0 < float(data["data"]["cloud_price_wish"]) < data["calculated"]["cloud_price_incl_refund"]:
        cloud_price = float(data["data"]["cloud_price_wish"])
        wish_price = True
    guarantee_runtime = ""
    if data["data"]["price_guarantee"] == "2_years":
        guarantee_runtime = "2 Jahre"
    if data["data"]["price_guarantee"] == "10_years":
        guarantee_runtime = "10 Jahre"
    if data["data"]["price_guarantee"] == "12_years":
        guarantee_runtime = "12 Jahre"
    light_cloud_usage = int(data["calculated"]["power_usage"])
    lightcloud_extra_price_per_kwh = float(data["calculated"]["lightcloud_extra_price_per_kwh"])
    cloud_label = "cCloud-Zero"
    cloud_description = "Mit der C.Cloud.ZERO – NULL Risiko<br>Genial einfach – einfach genial<br>Die sicherste Cloud Deutschlands.<br>Strom verbrauchen, wann immer Sie ihn brauchen."
    cloud_tarif = "cCloud-Zero"
    if "document_style" in data["data"]:
        if data["data"]["document_style"] == "bsh":
            cloud_label = "BSH-Cloud"
            cloud_description = "Genial einfach – einfach genial<br>Strom verbrauchen, wann immer Sie ihn brauchen."
            cloud_tarif = "BSH-Cloud"
        if data["data"]["document_style"] == "eeg":
            cloud_label = "EEG-Cloud"
            logo = render_template("offer/logo-eeg.html")
            cloud_description = f"<div style='float: right'>{logo}</div>Genial einfach – einfach genial<br>Strom verbrauchen, wann immer Sie ihn brauchen."
            cloud_tarif = "EEG-Cloud"
    offer_data["items"] = [
        {
            "label": cloud_label,
            "description": cloud_description,
            "quantity": 1,
            "quantity_unit": "mtl.",
            "tax_rate": tax_rate,
            "single_price": cloud_price,
            "single_price_net": cloud_price / (1 + tax_rate / 100),
            "single_tax_amount": cloud_price * (tax_rate / 100),
            "discount_rate": 0,
            "discount_single_amount": 0,
            "discount_single_price": cloud_price,
            "discount_single_price_net": cloud_price / (1 + tax_rate / 100),
            "discount_single_price_net_overwrite": None,
            "discount_single_tax_amount": cloud_price * (tax_rate / 100),
            "discount_total_amount": cloud_price,
            "total_price": cloud_price,
            "total_price_net": cloud_price / (1 + tax_rate / 100),
            "total_tax_amount": cloud_price * (tax_rate / 100),
        }
    ]
    offer_data["items"][0]["description"] = offer_data["items"][0]["description"] + "<br>\n<br>\n"\
        + f"Tarif: {cloud_tarif}<br>\n" \
        + f"Kündigungsfrist: {settings['data']['cloud_settings']['notice_period']}<br>\n" \
        + f"Vertragslaufzeit: {guarantee_runtime}<br>\n" \
        + f"garantierte Zero-Laufzeit für (a): {guarantee_runtime}<br>\n" \
        + f"Durch die Cloud abgedeckter Jahresverbrauch (a): {light_cloud_usage} kWh<br>\n" \
        + "<small>PV, Speicher & Netzbezug</small><br>\n" \
        + f"<small>Bei Mehrverbauch ist der Preis abhängig von der aktuellen Strompreisentwicklung derzeit {numberformat(lightcloud_extra_price_per_kwh * 100, digits=2)}&nbsp;cent&nbsp;/&nbsp;kWh</small>"
    offer_data["items"].append(monthly_price_product_base(
        description=pv_production,
        single_price=0))
    if data["calculated"]["cloud_price_heatcloud"] > 0:
        offer_data["items"].append(monthly_price_product_base(
            description=("<b>Wärmecloud</b><br>"
                         + f"Durch die Cloud abgedeckter Jahresverbrauch (a): {data['calculated']['heater_usage']} kWh<br>\n"
                         + f"<small>Bei Mehrverbauch ist der Preis abhängig von der aktuellen Strompreisentwicklung derzeit {numberformat(data['calculated']['heatcloud_extra_price_per_kwh'] * 100, digits=2)}&nbsp;cent&nbsp;/&nbsp;kWh</small>"),
            single_price=(0 if wish_price else data["calculated"]["cloud_price_heatcloud"])))
    if data["calculated"]["cloud_price_ecloud"] > 0:
        offer_data["items"].append(monthly_price_product_base(
            description=("<b>eCloud</b><br>"
                         + f"Durch die Cloud abgedeckter Jahresverbrauch (a): {data['calculated']['ecloud_usage']} kWh Gas<br>\n"
                         + f"<small>Bei Mehrverbauch ist der Preis abhängig von der aktuellen Gaspreisentwicklung derzeit {numberformat(data['calculated']['ecloud_extra_price_per_kwh'] * 100, digits=2)}&nbsp;cent&nbsp;/&nbsp;kWh</small>"),
            single_price=(0 if wish_price else data["calculated"]["cloud_price_ecloud"])))
    if data["calculated"]["cloud_price_consumer"] > 0:
        offer_data["items"].append(monthly_price_product_base(
            description=("<b>Consumer</b><br>"
                         + f"Durch die Cloud abgedeckter Jahresverbrauch (a): {data['calculated']['consumer_usage']} kWh<br>\n"
                         + f"<small>Bei Mehrverbauch ist der Preis abhängig von der aktuellen Strompreisentwicklung derzeit {numberformat(data['calculated']['consumercloud_extra_price_per_kwh'] * 100, digits=2)}&nbsp;cent&nbsp;/&nbsp;kWh</small>"),
            single_price=(0 if wish_price else data["calculated"]["cloud_price_consumer"])))
    if data["calculated"]["cloud_price_emove"] > 0:
        emove_description = ("<b>eMove</b><br>"
                             + f"Tarif: {data['data']['emove_tarif']}")
        if data['data']['emove_tarif'] == "emove.drive I":
            emove_description = ("<b>eMove</b><br>"
                                 + f"Tarif: {data['data']['emove_tarif']}<br>"
                                 + f"empfohlen bis ca. 8.000 km / Jahr<br>Laden Sie 500 kWh in der Home Area, und 1.000 kWh out of Home Area")
        if data['data']['emove_tarif'] == "emove.drive II":
            emove_description = ("<b>eMove</b><br>"
                                 + f"Tarif: {data['data']['emove_tarif']}<br>"
                                 + f"empfohlen bis ca. 12.000 km / Jahr<br>Laden Sie 1.000 kWh in der Home Area, und 1.000 kWh out of Home Area")
        if data['data']['emove_tarif'] == "emove.drive III":
            emove_description = ("<b>eMove</b><br>"
                                 + f"Tarif: {data['data']['emove_tarif']}<br>"
                                 + f"empfohlen bis ca. 20.000 km / Jahr<br>Laden Sie 2.000 kWh in der Home Area, und 3.000 kWh out of Home Area")
        if data['data']['emove_tarif'] == "emove.drive ALL":
            emove_description = ("<b>eMove</b><br>"
                                 + f"Tarif: {data['data']['emove_tarif']}<br>"
                                 + f"empfohlen bis ca. 25.000 km / Jahr<br>Laden Sie 2.500 kWh in der Home Area, und 6.000 kWh out of Home Area")
        offer_data["items"].append(monthly_price_product_base(
            description=emove_description,
            single_price=(0 if wish_price else data["calculated"]["cloud_price_emove"])))
    if data["calculated"]["cloud_price_extra"] > 0:
        offer_data["items"].append(monthly_price_product_base(
            description=("<b>Minderverbau</b><br>"
                         + f"PV-Anlage um {numberformat(-data['calculated']['kwp_extra'])} kWp zu klein"),
            single_price=(0 if wish_price else data["calculated"]["cloud_price_extra"])))
    if data["calculated"]["cloud_price_extra"] < 0:
        offer_data["items"].append(monthly_price_product_base(
            description=("<b>Mehrverbau</b><br>"
                         + f"PV-Anlage um {numberformat(data['calculated']['kwp_extra'])} kWp größer"),
            single_price=(0 if wish_price else data["calculated"]["cloud_price_extra"])))
    if "zero_option" in data["data"] and data["data"]["zero_option"] is True:
        offer_data["items"].append(monthly_price_product_base(
            description="<b>ZERO-Paket</b>",
            single_price=-cloud_price))
    offer_data["items"].append(monthly_price_product_base(
        description=(
            "<b>Cashback</b><br>"
            + "Wird weniger Strom verbraucht als bei (a) vereinbart,<br>"
            + "so erhalten Sie 10 Cent inkl. MwSt als Energiespar-Bonus von uns zurück.<br>"
            + "Die ersten 250 kWh bleiben davon ausgenommen."),
        single_price=0))
    if data["calculated"]["cloud_price_ecloud"] > 0:
        offer_data["items"].append(monthly_price_product_base(
            description=(
                "<b>Cashback eCloud</b><br>"
                + "Wird weniger Gas verbraucht als bei (a) vereinbart,<br>"
                + "so erhalten Sie 4 Cent inkl. MwSt als Energiespar-Bonus von uns zurück.<br>"
                + "Die ersten 250 kWh bleiben davon ausgenommen."),
            single_price=0))

    return offer_data["items"]


def cloud_offer_calculation_by_pv_offer(offer: OfferV2):
    settings = get_settings("pv-settings")
    if settings is None:
        return None
    offer_data = base_offer_data("cloud-offer", offer.survey)
    data = {
        # "pv_kwp": None,
        "power_usage": offer.survey.data["pv_usage"],
        "consumers": [],
        "price_guarantee": "12_years"
    }
    packet_number = math.ceil(int(offer.survey.data["pv_usage"]) / 500) * 5
    pv_kwp = None
    if int(offer.survey.data["max_packet_number"]) > 0 and int(offer.survey.data["max_packet_number"]) < packet_number:
        settings = get_settings("pv-settings")
        packet_number = int(offer.survey.data["max_packet_number"])
        pv_kwp = packet_number * 100 * settings["data"]["cloud_settings"]["power_to_kwp_factor"] / 1000
        data["pv_kwp"] = pv_kwp
    if "has_heatcloud" in offer.survey.data and offer.survey.data["has_heatcloud"] and "heatcloud_usage" in offer.survey.data:
        data["heater_usage"] = offer.survey.data["heatcloud_usage"]
    if "has_ecloud" in offer.survey.data and offer.survey.data["has_ecloud"] and "ecloud_usage" in offer.survey.data:
        data["ecloud_usage"] = offer.survey.data["ecloud_usage"]
    if "cloud_emove" in offer.survey.data:
        data["emove_tarif"] = offer.survey.data["cloud_emove"]
    if "has_extra_drains" in offer.survey.data and offer.survey.data["has_extra_drains"]:
        for drain in offer.survey.data["extra_drains"]:
            if "usage" in drain and drain["usage"] != "" and int(drain["usage"]) > 0:
                data["consumers"].append(drain)
    if "pv_options" in offer.survey.data:
        for optional_product in offer.survey.data["pv_options"]:
            if optional_product["label"] == "ZERO-Paket" and "is_selected" in optional_product and optional_product["is_selected"]:
                data["zero_option"] = True
    offer_data["calculated"] = calculate_cloud(data=data)
    return offer_data["calculated"]


def cloud_offer_items_by_pv_offer(offer: OfferV2):
    settings = get_settings("pv-settings")
    if settings is None:
        return None
    offer_data = base_offer_data("cloud-offer", offer.survey)
    data = {
        # "pv_kwp": None,
        "power_usage": offer.survey.data["pv_usage"],
        "consumers": [],
        "price_guarantee": "12_years"
    }
    if "price_guarantee" in offer.survey.data:
        data["price_guarantee"] = offer.survey.data["price_guarantee"]

    packet_number = math.ceil(int(offer.survey.data["pv_usage"]) / 500) * 5
    pv_kwp = None
    if int(offer.survey.data["max_packet_number"]) > 0 and int(offer.survey.data["max_packet_number"]) < packet_number:
        settings = get_settings("pv-settings")
        packet_number = int(offer.survey.data["max_packet_number"])
        pv_kwp = ((packet_number * 100) * settings["data"]["cloud_settings"]["power_to_kwp_factor"]) / 1000
    if pv_kwp is not None:
        data["pv_kwp"] = pv_kwp
    if "has_heatcloud" in offer.survey.data and offer.survey.data["has_heatcloud"] and "heatcloud_usage" in offer.survey.data:
        data["heater_usage"] = offer.survey.data["heatcloud_usage"]
    if "has_ecloud" in offer.survey.data and offer.survey.data["has_ecloud"] and "ecloud_usage" in offer.survey.data:
        data["ecloud_usage"] = offer.survey.data["ecloud_usage"]
    if "cloud_emove" in offer.survey.data:
        data["emove_tarif"] = offer.survey.data["cloud_emove"]
    if "has_extra_drains" in offer.survey.data and offer.survey.data["has_extra_drains"]:
        for drain in offer.survey.data["extra_drains"]:
            if "usage" in drain and drain["usage"] != "" and int(drain["usage"]) > 0:
                data["consumers"].append(drain)
    if "pv_options" not in offer.survey.data:
        offer.survey.data["pv_options"] = []
    for optional_product in offer.survey.data["pv_options"]:
        if optional_product["label"] == "ZERO-Paket" and "is_selected" in optional_product and optional_product["is_selected"]:
            data["zero_option"] = True
    offer_data["calculated"] = calculate_cloud(data=data)
    offer_data["items"] = get_cloud_products(data={
        "data": data,
        "calculated": offer_data["calculated"]
    }, offer=offer)
    return offer_data["items"]


def monthly_price_product_base(description, single_price):
    taxrate = 19
    return {
        "label": "",
        "description": description,
        "quantity": 1,
        "quantity_unit": "mtl.",
        "tax_rate": taxrate,
        "single_price": single_price,
        "single_price_net": single_price / (1 + (taxrate / 100)),
        "single_tax_amount": single_price * (taxrate / 100),
        "discount_rate": 0,
        "discount_single_amount": 0,
        "discount_single_price": single_price,
        "discount_single_price_net": single_price / (1 + (taxrate / 100)),
        "discount_single_price_net_overwrite": None,
        "discount_single_tax_amount": single_price * (taxrate / 100),
        "discount_total_amount": single_price,
        "total_price": single_price,
        "total_price_net": single_price / (1 + (taxrate / 100)),
        "total_tax_amount": single_price * (taxrate / 100)
    }
