from app.models import OfferV2, Survey, Settings, Lead

from ..add_update_item import add_item_v2
from ._utils import base_offer_data, add_item_to_offer, add_optional_item_to_offer


def pv_offer_by_survey(survey: Survey, old_data=None):
    offer = None
    if survey.data["pv_usage"] is not None and \
        survey.data["pv_usage"] != "" and \
        int(survey.data["pv_usage"]) > 0 and \
        (
            old_data is None
            or survey.data["pv_usage"] != old_data["data"]["pv_usage"]):

        offer_data = base_offer_data("pv-offer", survey)

        product_name = "PV Paket {}".format(survey.data["packet_number"])
        for optional_product in survey.data["pv_options"]:
            if optional_product["label"] == "Schwarze Module":
                product_name = "PV Paket {}".format(survey.data["packet_number"])
                break
        if survey.data["pv_module_type"] == "390":
            product_name = "PV Paket {} (390)".format(survey.data["packet_number"])
        if survey.data["pv_module_type"] == "400":
            product_name = "PV Paket {} (400)".format(survey.data["packet_number"])

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
            offer_data = add_item_to_offer(
                survey,
                offer_data,
                "Akku Stag 2,5 kW",
                "Erneuerbare Energie - Cloud PV Pakete Optionen",
                quantity)

        integrated_options = ["Schwarze Module"]
        for optional_product in survey.data["pv_options"]:
            if optional_product["label"] not in integrated_options:
                integrated_options.append(optional_product["label"])
                offer_data = add_optional_item_to_offer(
                    survey,
                    offer_data,
                    optional_product
                )

        optional_products = Settings.query.filter(Settings.section == 'pv-settings').first()
        optional_products = optional_products.data["pv_settings"]["optional_products"]
        for optional_product in optional_products:
            if optional_product["label"] not in integrated_options and "include_always" in optional_product and optional_product["include_always"] in ["top", "bottom"]:
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
