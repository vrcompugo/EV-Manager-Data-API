import json
import math

from app.models import OfferV2, Survey, Settings, Lead

from ..add_update_item import add_item_v2
from ._utils import base_offer_data, add_item_to_offer, add_optional_item_to_offer


def roof_offer_by_survey(survey: Survey, old_data=None):
    offer = None

    if "roof_reconstrution_same_as_pv" not in survey.data or not survey.data["roof_reconstrution_same_as_pv"]:
        if "roof_reconstrution_sqm" not in survey.data:
            print("no roof sqm given")
            return None
        roof_sqm = int(survey.data["roof_reconstrution_sqm"])
    else:
        roof_sqm = 0
        if "extra_roof_main" in survey.data and survey.data["extra_roof_main"] and "extra_roof_main_m2" in survey.data and survey.data["extra_roof_main_m2"] != "":
            roof_sqm = roof_sqm + int(survey.data["extra_roof_main_m2"])
        if "extra_roof_garage" in survey.data and survey.data["extra_roof_garage"] and "extra_roof_garage_m2" in survey.data and survey.data["extra_roof_garage_m2"] != "":
            roof_sqm = roof_sqm + int(survey.data["extra_roof_garage_m2"])
        if "extra_roof_gardenhouse" in survey.data and survey.data["extra_roof_gardenhouse"] and "extra_roof_gardenhouse_m2" in survey.data and survey.data["extra_roof_gardenhouse_m2"] != "":
            roof_sqm = roof_sqm + int(survey.data["extra_roof_gardenhouse_m2"])
        if "extra_roof_other" in survey.data and survey.data["extra_roof_other"] and "extra_roof_other_m2" in survey.data and survey.data["extra_roof_other_m2"] != "":
            roof_sqm = roof_sqm + int(survey.data["extra_roof_other_m2"])
    roof_sqm = int(roof_sqm)
    offer_data = base_offer_data("roof-offer", survey)

    product_name = "Dachsanierung Paket"
    if "roof_type" in survey.data and survey.data["roof_type"] == "flat":
        product_name = "Flachdachsanierung"
    if "roof_dampening" in survey.data and survey.data["roof_dampening"]:
        product_name = product_name + " mit Dämmung"

    offer_data = add_item_to_offer(
        survey,
        offer_data,
        product_name,
        "Erneuerbare Energie - Dach",
        roof_sqm
    )

    if "roof_asbest" in survey.data and survey.data["roof_asbest"]:
        offer_data = add_item_to_offer(
            survey,
            offer_data,
            "Asbestzementplatten abnehmen und entsorgen",
            "Erneuerbare Energie - Dach",
            roof_sqm
        )
    else:
        offer_data = add_item_to_offer(
            survey,
            offer_data,
            "Asbestzementplatten abnehmen und entsorgen",
            "Erneuerbare Energie - Dach",
            0
        )

    options = [
        "Abfallentsorgung",
        "Dacharbeiten zusätzlich"
        ]
    for option in options:
        offer_data = add_item_to_offer(
            survey,
            offer_data,
            option,
            "Erneuerbare Energie - Dach",
            1
        )
    options = [
        "Abnehmen des Schneefanges",
        "Alte Dachrinne und Fallrohr abnehmen",
        "Ausstiegsfenster ausbauen und entsorgen",
        "Kamin komplett abnehmen und entsorgen",
        "Neue Dachrinne aus Zinkblech",
        "Sat Anlage Versetzen",
        "Schiefer arbeiten",
        "Schneefang",
        "Schneefang für Photovoltaik",
        "Schornstein verschiefern",
        "Wohndachfenster ausbauen und entsorgen",
        "Wohndachfenster einbauen"
    ]
    for option in options:
        offer_data = add_item_to_offer(
            survey,
            offer_data,
            option,
            "Erneuerbare Energie - Dach",
            0,
            position="bottom"
        )

    lead = Lead.query.filter(Lead.customer_id == survey.customer.id).first()
    if lead is not None:
        offer_data["lead_id"] = lead.id
    offer = add_item_v2(offer_data)

    return offer
