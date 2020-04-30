import json
import math

from app.models import OfferV2, Survey, Settings, Lead

from ..add_update_item import add_item_v2
from ._utils import base_offer_data, add_item_to_offer, add_optional_item_to_offer


def heater_offer_by_survey(survey: Survey, old_data=None):
    offer = None
    if (
        "heating_sqm" in survey.data and survey.data["heating_sqm"] is not None
        and survey.data["heating_sqm"] != ""
        and int(survey.data["heating_sqm"]) > 0
    ):

        offer_data = base_offer_data("heater-offer", survey)
        heater_kw = int(int(survey.data["heating_sqm"]) * int(survey.data["house_damping"]) / 1000)

        if survey.data["heater_type"] == "oil":
            offer_data = add_item_to_offer(
                survey,
                offer_data,
                "Öl Heizung",
                "Heizung - Öl",
                1,
                packet_number=heater_kw
            )
        if survey.data["heater_type"] == "gas":
            product_name = "HANSA Gas Pega"
            if survey.data["people_in_house"] == "1-3":
                product_name = "HANSA Gas"
            offer_data = add_item_to_offer(
                survey,
                offer_data,
                product_name,
                "Heizung - Gas",
                1,
                packet_number=heater_kw
            )
        if survey.data["heater_type"] == "wp":
            product_name = "Luft-Wasser Wärmepumpe Bestand"
            if survey.data["house_construction_year"] == "2016-newer":
                product_name = "Neubau Wärmepumpe Komplettpaket"
            offer_data = add_item_to_offer(
                survey,
                offer_data,
                product_name,
                "Heizung - WP",
                1,
                packet_number=heater_kw
            )

        if survey.data["heater_type"] in ["oil", "gas"]:
            person_number = 1
            if survey.data["people_in_house"] == "4-5":
                person_number = 4
            if survey.data["people_in_house"] == "6-8":
                person_number = 6
            if survey.data["people_in_house"] == "more_than_8":
                person_number = 9
            product_name = "Brauchwasserspeicher"
            if "offer_solarthermie" in survey.data and survey.data["offer_solarthermie"]:
                product_name = "Schichtenspeicher"
            offer_data = add_item_to_offer(
                survey,
                offer_data,
                product_name,
                "Heizung - Optionen für Heizung",
                1,
                packet_number=person_number
            )
        if survey.data["heater_type"] == "wp":
            if "offer_solarthermie" in survey.data and survey.data["offer_solarthermie"]:
                offer_data = add_item_to_offer(
                    survey,
                    offer_data,
                    "Schichtenspeicher",
                    "Heizung - Optionen für Heizung",
                    1
                )

        if "offer_solarthermie" in survey.data and survey.data["offer_solarthermie"]:
            offer_data = add_item_to_offer(
                survey,
                offer_data,
                "Solarthermie Set",
                "Heizung - Solarthermie",
                1,
                packet_number=int(survey.data["solarthermie_sqm"])
            )

        if survey.data["heater_type"] == "oil":
            label_type = "Öl"
            products = [["Systemtrenner Auslaufventil Öl", 1], ["Hydraulischer Abgleich Öl", 1], ["Hydraulischer Abgleich Öl II", 1]]
            product_folder = "Heizung - Öl"
        if survey.data["heater_type"] == "gas":
            label_type = "Gas"
        if survey.data["heater_type"] == "wp":
            label_type = "WP"

        offer_data = add_item_to_offer(
            survey,
            offer_data,
            f"Systemtrenner Auslaufventil {label_type}",
            f"Heizung - {label_type}",
            1
        )

        if survey.data["heater_type"] == "wp":
            label_type = "WP"
            offer_data = add_item_to_offer(
                survey,
                offer_data,
                "WP Elektrik",
                "Heizung - WP",
                1
            )
            offer_data = add_item_to_offer(
                survey,
                offer_data,
                "WP Inbetriebnahme",
                "Heizung - WP",
                1
            )
            offer_data = add_item_to_offer(
                survey,
                offer_data,
                "WP Befestigung",
                "Heizung - WP",
                0
            )

        offer_data = add_item_to_offer(
            survey,
            offer_data,
            f"Hydraulischer Abgleich {label_type}",
            f"Heizung - {label_type}",
            0,
            position="top"
        )
        offer_data = add_item_to_offer(
            survey,
            offer_data,
            f"Hydraulischer Abgleich {label_type} II",
            f"Heizung - {label_type}",
            0,
            position="top"
        )

        lead = Lead.query.filter(Lead.customer_id == survey.customer.id).first()
        if lead is not None:
            offer_data["lead_id"] = lead.id
        offer = add_item_v2(offer_data)

    return offer
