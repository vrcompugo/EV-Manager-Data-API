import json
import math

from app.models import OfferV2, Survey, Settings, Lead

from ..add_update_item import add_item_v2
from ._utils import base_offer_data, add_item_to_offer, add_optional_item_to_offer
from app.modules.cloud.services.calculation import calculate_cloud


def pv_offer_by_survey(survey: Survey, old_data=None):
    offer = None
    survey.data["pv_usage"] = int(survey.data["pv_usage"])
    offer_data = base_offer_data("pv-offer", survey)
    packet_number = math.ceil(survey.data["pv_usage"] / 500) * 5
    if packet_number < 25:
        packet_number = 25
    if packet_number > 300:
        packet_number = 300
    product_name = "PV Paket {}".format(packet_number)
    if survey.data["pv_module_type"] == "390":
        product_name = "PV Paket {} (390)".format(packet_number)
    if survey.data["pv_module_type"] == "400":
        product_name = "PV Paket {} (400)".format(packet_number)

    offer_data = add_item_to_offer(
        survey,
        offer_data,
        product_name,
        "Erneuerbare Energie - Cloud PV Pakete",
        1
    )

    if int(packet_number) >= 35:
        quantity = 1
        if int(packet_number) == 35 and survey.data["pv_module_type"] == "280":
            quantity = 0
        if 65 <= int(packet_number) <= 70:
            quantity = 2
        if 75 <= int(packet_number) <= 85:
            quantity = 3
        if 90 <= int(packet_number) <= 125:
            quantity = 4
        if 130 <= int(packet_number) <= 155:
            quantity = 5
        if 160 <= int(packet_number) <= 180:
            quantity = 6
        if 185 <= int(packet_number) <= 220:
            quantity = 7
        if 230 <= int(packet_number) <= 300:
            quantity = 9
        if int(packet_number) > 300:
            total_usage = int(survey.data["pv_usage"])
            if "extra_drains" in survey.data:
                for drain in survey.data["extra_drains"]:
                    if drain["usage"] != "":
                        total_usage = total_usage + int(drain["usage"])
            quantity = 9 + math.ceil((total_usage - 30000) / 5000)
            if quantity > 27:
                quantity = 27
            extra_modules = math.ceil((total_usage - 30000) / 500) * 5
            if survey.data["pv_module_type"] == "400":
                extra_modules = math.ceil((total_usage - 30000) / 500) * 3
            if extra_modules > 0:
                offer_data = add_item_to_offer(
                    survey,
                    offer_data,
                    f"zusätzliches {survey.data['pv_module_type']}Watt Modul",
                    "Erneuerbare Energie - Cloud PV Pakete Optionen",
                    extra_modules)
        if quantity > 0:
            offer_data = add_item_to_offer(
                survey,
                offer_data,
                "Akku Stag 2,5 kW",
                "Erneuerbare Energie - Cloud PV Pakete Optionen",
                quantity)

    cloud_data = {
        "power_usage": survey.data["pv_usage"],
        "consumers": []
    }
    extra_kwp = 0
    if "has_heatcloud" in survey.data and survey.data["has_heatcloud"] and "heatcloud_usage" in survey.data and survey.data["heatcloud_usage"] != "":
        cloud_data["heater_usage"] = int(survey.data["heatcloud_usage"])
    if "has_ecloud" in survey.data and survey.data["has_ecloud"] and "ecloud_usage" in survey.data and survey.data["ecloud_usage"] != "":
        cloud_data["ecloud_usage"] = int(survey.data["ecloud_usage"])
    if "extra_drains" in survey.data:
        for drain in survey.data["extra_drains"]:
            if "usage" in drain and drain["usage"] != "" and int(drain["usage"]) > 0:
                cloud_data["consumers"].append(drain)

    try:
        cloud_data = calculate_cloud(cloud_data)
    except Exception as e:
        return pv_offer_by_survey_old(survey=survey, old_data=old_data)

    extra_kwp = cloud_data["min_kwp"] - cloud_data["min_kwp_light"]
    if extra_kwp > 0:
        if survey.data["pv_module_type"] == "280":
            offer_data = add_item_to_offer(
                survey,
                offer_data,
                "zusätzliches 280Watt Modul",
                "Erneuerbare Energie - Cloud PV Pakete Optionen",
                math.ceil(extra_kwp / 0.28))
        if survey.data["pv_module_type"] == "400":
            offer_data = add_item_to_offer(
                survey,
                offer_data,
                "zusätzliches 400Watt Modul",
                "Erneuerbare Energie - Cloud PV Pakete Optionen",
                math.ceil(extra_kwp / 0.4))

    if "cloud_emove" in survey.data and survey.data["cloud_emove"] != "":
        emove_label = None
        if survey.data["cloud_emove"] == "emove.drive I":
            emove_label = "e.move.drive I"
        if survey.data["cloud_emove"] == "emove.drive II":
            emove_label = "e.move.drive III"
        if survey.data["cloud_emove"] == "emove.drive III":
            emove_label = "e.move.drive III"
        if survey.data["cloud_emove"] == "emove.drive ALL":
            emove_label = "e.move.drive all"
        if emove_label is not None:
            offer_data = add_item_to_offer(
                survey,
                offer_data,
                emove_label,
                "Erneuerbare Energie - Cloud PV Pakete Optionen",
                1)

    integrated_options = []
    for optional_product in survey.data["pv_options"]:
        if (optional_product["label"] not in integrated_options
            and (
                (
                    "is_selected" in optional_product
                    and optional_product["is_selected"])
                or (
                    "include_always" in optional_product
                    and optional_product["include_always"] in ["top", "bottom"]))):

            integrated_options.append(optional_product["label"])
            offer_data = add_optional_item_to_offer(
                survey,
                offer_data,
                optional_product
            )

    lead = Lead.query.filter(Lead.customer_id == survey.customer.id).order_by(Lead.id.desc()).first()
    if lead is not None:
        offer_data["lead_id"] = lead.id
    offer = add_item_v2(offer_data)

    return offer


def pv_offer_by_survey_old(survey: Survey, old_data=None):
    offer = None
    if (
            survey.data["pv_usage"] is not None
            and survey.data["pv_usage"] != ""
            and int(survey.data["pv_usage"]) > 0):

        offer_data = base_offer_data("pv-offer", survey)
        packet_number = survey.data["offered_packet_number"]
        if int(survey.data["offered_packet_number"]) > 300:
            packet_number = 300
        product_name = "PV Paket {}".format(packet_number)
        if survey.data["pv_module_type"] == "390":
            product_name = "PV Paket {} (390)".format(packet_number)
        if survey.data["pv_module_type"] == "400":
            product_name = "PV Paket {} (400)".format(packet_number)

        offer_data = add_item_to_offer(
            survey,
            offer_data,
            product_name,
            "Erneuerbare Energie - Cloud PV Pakete",
            1
        )

        if int(survey.data["packet_number"]) >= 35:
            quantity = 1
            if int(survey.data["packet_number"]) == 35 and survey.data["pv_module_type"] == "280":
                quantity = 0
            if 65 <= int(survey.data["packet_number"]) <= 70:
                quantity = 2
            if 75 <= int(survey.data["packet_number"]) <= 85:
                quantity = 3
            if 90 <= int(survey.data["packet_number"]) <= 125:
                quantity = 4
            if 130 <= int(survey.data["packet_number"]) <= 155:
                quantity = 5
            if 160 <= int(survey.data["packet_number"]) <= 180:
                quantity = 6
            if 185 <= int(survey.data["packet_number"]) <= 220:
                quantity = 7
            if 230 <= int(survey.data["packet_number"]) <= 300:
                quantity = 9
            if int(survey.data["packet_number"]) > 300:
                total_usage = int(survey.data["pv_usage"])
                if "extra_drains" in survey.data:
                    for drain in survey.data["extra_drains"]:
                        if drain["usage"] != "":
                            total_usage = total_usage + int(drain["usage"])
                quantity = 9 + math.ceil((total_usage - 30000) / 5000)
                if quantity > 27:
                    quantity = 27
                extra_modules = math.ceil((total_usage - 30000) / 500) * 5
                if survey.data["pv_module_type"] == "400":
                    extra_modules = math.ceil((total_usage - 30000) / 500) * 3
                if extra_modules > 0:
                    offer_data = add_item_to_offer(
                        survey,
                        offer_data,
                        f"zusätzliches {survey.data['pv_module_type']}Watt Modul",
                        "Erneuerbare Energie - Cloud PV Pakete Optionen",
                        extra_modules)
            if quantity > 0:
                offer_data = add_item_to_offer(
                    survey,
                    offer_data,
                    "Akku Stag 2,5 kW",
                    "Erneuerbare Energie - Cloud PV Pakete Optionen",
                    quantity)

        integrated_options = []
        for optional_product in survey.data["pv_options"]:
            if (optional_product["label"] not in integrated_options
                and (
                    (
                        "is_selected" in optional_product
                        and optional_product["is_selected"])
                    or (
                        "include_always" in optional_product
                        and optional_product["include_always"] in ["top", "bottom"]))):

                integrated_options.append(optional_product["label"])
                offer_data = add_optional_item_to_offer(
                    survey,
                    offer_data,
                    optional_product
                )

        lead = Lead.query.filter(Lead.customer_id == survey.customer.id).order_by(Lead.id.desc()).first()
        if lead is not None:
            offer_data["lead_id"] = lead.id
        offer = add_item_v2(offer_data)
    else:
        print("usage missing")

    return offer
