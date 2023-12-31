import json
import math

from app.models import OfferV2, Survey, Settings, Lead

from ..add_update_item import add_item_v2
from ._utils import base_offer_data, add_item_to_offer, add_optional_item_to_offer


def storage_offer_by_survey(survey: Survey, old_data=None):
    offer = None
    if survey.data["pv_usage"] is not None and \
        survey.data["pv_usage"] != "" and \
        int(survey.data["pv_usage"]) > 0 and \
        (
            old_data is None
            or survey.data["pv_usage"] != old_data["data"]["pv_usage"]):

        offer_data = base_offer_data("pv-offer", survey)
        packet_number = survey.data["packet_number"]
        if int(survey.data["packet_number"]) > 300:
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

        lead = Lead.query.filter(Lead.customer_id == survey.customer.id).first()
        if lead is not None:
            offer_data["lead_id"] = lead.id
        offer = add_item_v2(offer_data)

    return offer
