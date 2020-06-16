import math

from app.models import OfferV2
from app.modules.settings.settings_services import get_one_item as get_settings
from app.modules.auth.auth_services import get_logged_in_user

from app.modules.offer.services.offer_generation._utils import base_offer_data, add_item_to_offer, add_optional_item_to_offer

def calculate_cloud(data):
    settings = get_settings("pv-settings")
    if settings is None:
        return None
    user = get_logged_in_user()
    print(user, data)
    settings["data"]["cloud_settings"] = {
        "power_to_kwp_factor": 1.78,
        "heater_to_kwp_factor": [
            {"from": 0, "to": 4000, "value": 1.77},
            {"from": 4001, "to": 6500, "value": 1.88},
            {"from": 6501, "to": 9999999, "value": 1.98}
        ],
        "consumer_to_kwp_factor": 1.979,
        "kwp_to_refund_factor": 6.225,
        "cloud_user_prices": {
            113: [
                {"from": 0, "to": 7000, "value": 25},
                {"from": 7001, "to": 15000, "value": 34},
                {"from": 15001, "to": 20000, "value": 59},
                {"from": 20001, "to": 35000, "value": 89},
                {"from": 35001, "to": 50000, "value": 149},
                {"from": 50001, "to": 55000, "value": 199},
                {"from": 55001, "to": 9999999, "value": 9999},
            ]
        },
        "cloud_user_heater_prices": {
            113: [
                {"from": 0, "to": 4000, "value": 25},
                {"from": 4001, "to": 6500, "value": 29},
                {"from": 6501, "to": 9000, "value": 39},
                {"from": 9001, "to": 999999, "value": 49}
            ]
        },
        "cloud_user_consumer_prices": {
            113: [
                {"from": 0, "to": 3000, "value": 22},
                {"from": 3001, "to": 4500, "value": 25},
                {"from": 4501, "to": 6500, "value": 29},
                {"from": 6501, "to": 9000, "value": 49},
                {"from": 9001, "to": 15000, "value": 69},
                {"from": 15001, "to": 25000, "value": 89},
                {"from": 25001, "to": 35000, "value": 149},
                {"from": 35001, "to": 55000, "value": 199},
                {"from": 35001, "to": 55000, "value": 199},
                {"from": 55001, "to": 75000, "value": 299},
                {"from": 75001, "to": 99000, "value": 399},
                {"from": 99001, "to": 999999, "value": 1999}
            ]
        },
        "cloud_emove": {
            "emove Tarif Hybrid": {"price": 9.99, "kwp": 0},
            "emove.drive": {"price": 9.99, "kwp": 3},
            "emove.drive I": {"price": 9.99, "kwp": 4},
            "emove.drive II": {"price": 19.99, "kwp": 6.5},
            "emove.drive ALL": {"price": 39.00, "kwp": 7},
        },
        "cloud_guarantee": {
            113: {
                "10_years": {"price": 399}
            }
        }
    }
    min_kwp = 0
    storage_size = 0
    cloud_price = 0
    cloud_price_refund = 0
    user_one_time_cost = 0
    if "power_usage" in data:
        data["power_usage"] = int(data["power_usage"])
        min_kwp = data["power_usage"] * settings["data"]["cloud_settings"]["power_to_kwp_factor"] / 1000
        storage_size = round(data["power_usage"] / 1000)
        cloud_price = list(filter(
            lambda item: item['from'] <= data["power_usage"] and data["power_usage"] <= item['to'],
            settings["data"]["cloud_settings"]["cloud_user_prices"][user["id"]]
        ))[0]["value"]
    if "heater_usage" in data:
        data["heater_usage"] = int(data["heater_usage"])
        heater_to_kwp_factor = list(filter(
            lambda item: item['from'] <= data["heater_usage"] and data["heater_usage"] <= item['to'],
            settings["data"]["cloud_settings"]["heater_to_kwp_factor"]
        ))[0]["value"]
        cloud_price = cloud_price + list(filter(
            lambda item: item['from'] <= data["heater_usage"] and data["heater_usage"] <= item['to'],
            settings["data"]["cloud_settings"]["cloud_user_heater_prices"][user["id"]]
        ))[0]["value"]
        min_kwp = min_kwp + (data["heater_usage"] * heater_to_kwp_factor / 1000)
    if "consumers" in data:
        consumer_usage = 0
        for consumer in data["consumers"]:
            consumer_usage = consumer_usage + int(consumer["usage"])
            consumer_price = list(filter(
                lambda item: item['from'] <= int(consumer["usage"]) and int(consumer["usage"]) <= item['to'],
                settings["data"]["cloud_settings"]["cloud_user_consumer_prices"][user["id"]]
            ))
            if len(consumer_price) > 0:
                cloud_price = cloud_price + consumer_price[0]["value"]
        min_kwp = min_kwp + (consumer_usage * settings["data"]["cloud_settings"]["consumer_to_kwp_factor"]) / 1000

    if "emove_tarif" in data:
        if data["emove_tarif"] in settings["data"]["cloud_settings"]["cloud_emove"]:
            min_kwp = min_kwp + settings["data"]["cloud_settings"]["cloud_emove"][data["emove_tarif"]]["kwp"]
            cloud_price = cloud_price + settings["data"]["cloud_settings"]["cloud_emove"][data["emove_tarif"]]["price"]

    if "pv_kwp" in data:
        data["pv_kwp"] = float(data["pv_kwp"])
        if data["pv_kwp"] > min_kwp:
            extra_kwp = data["pv_kwp"] - min_kwp
            cloud_price_refund = extra_kwp * settings["data"]["cloud_settings"]["kwp_to_refund_factor"]
    if "price_guarantee" in data:
        if user["id"] in settings["data"]["cloud_settings"]["cloud_guarantee"]:
            if data["price_guarantee"] in settings["data"]["cloud_settings"]["cloud_guarantee"][user["id"]]:
                user_one_time_cost = user_one_time_cost + settings["data"]["cloud_settings"]["cloud_guarantee"][user["id"]][data["price_guarantee"]]["price"]
    return {
        "min_kwp": min_kwp,
        "storage_size": storage_size,
        "cloud_price": cloud_price,
        "cloud_price_incl_refund": cloud_price - cloud_price_refund,
        "user_one_time_cost": user_one_time_cost
    }


def cloud_offer_items_by_pv_offer(offer: OfferV2):
    settings = get_settings("pv-settings")
    if settings is None:
        return None
    offer_data = base_offer_data("cloud-offer", offer.survey)
    total_drain = int(offer.survey.data['pv_usage'])
    if "has_extra_drains" in offer.survey.data and offer.survey.data["has_extra_drains"]:
        for drain in offer.survey.data["extra_drains"]:
            if "usage" in drain and drain["usage"] != "" and int(drain["usage"]) > 0:
                total_drain = total_drain + int(drain["usage"])
    extra_usage = 0
    if total_drain > int(offer.survey.data['offered_usage']):
        extra_usage = total_drain - int(offer.survey.data['offered_usage'])
    tax_rate = 19
    cloud_price = 99
    for price in settings["data"]["cloud_settings"]["cloud_prices"]:
        if int(price["paket_range_start"]) <= int(offer.survey.data["offered_packet_number"]) <= int(price["paket_range_end"]):
            cloud_price = float(price["price"])
    offer_data["items"] = [
        {
            "label": "cCloud-Zero",
            "description": "Mit der C.Cloud.ZERO – NULL Risiko<br>Genial einfach – einfach genial<br>Die sicherste Cloud Deutschlands.<br>Stromverbrauchen, wann immer Sie ihn brauchen.",
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
        + "Tarif: cCloud-Zero<br>\n" \
        + f"Kündigungsfrist: {settings['data']['cloud_settings']['notice_period']}<br>\n" \
        + f"Vertragslaufzeit: {settings['data']['cloud_settings']['contract_run_time']}<br>\n" \
        + f"garantierte Zero-Laufzeit für (a): {settings['data']['cloud_settings']['guaranteed_run_time']}<br>\n" \
        + f"Durch die Cloud abgedeckter Jahresverbrauch: {offer.survey.data['offered_usage']} kWh<br>\n" \
        + "<small>PV, Speicher & Netzbezug</small><br>\n" \
        + f"<small>Bei Mehrverbauch ist der Preis abhängig von der aktuellen Strompreisentwicklung derzeit {settings['data']['cloud_settings']['extra_kwh_cost']} cent / kWh</small>"
    offer_data["items"].append({
        "label": "",
        "description": (
            "<b>PV Erzeugung</b><br>\n"
            + f"Zählernummer: {offer.survey.data['current_counter_number']}<br>\n"
            + f"PV-Anlage laut Angebot: PV-{offer.id}<br>\n"
            + f"{offer.survey.data['street']} {offer.survey.data['zip']} {offer.survey.data['city']}<br>\n"
            + f"Abnahme: {offer.survey.data['pv_usage']} kWh<br>\n"
        ),
        "quantity": 1,
        "quantity_unit": "mtl.",
        "tax_rate": 19,
        "single_price": 0,
        "single_price_net": 0,
        "single_tax_amount": 0,
        "discount_rate": 0,
        "discount_single_amount": 0,
        "discount_single_price": 0,
        "discount_single_price_net": 0,
        "discount_single_price_net_overwrite": None,
        "discount_single_tax_amount": 0,
        "discount_total_amount": 0,
        "total_price": 0,
        "total_price_net": 0,
        "total_tax_amount": 0
    })

    if "has_extra_drains" in offer.survey.data and offer.survey.data["has_extra_drains"]:
        for drain in offer.survey.data["extra_drains"]:
            if "usage" in drain and drain["usage"] != "" and int(drain["usage"]) > 0:
                offer_data["items"].append({
                    "label": "Zählergrundgebühr",
                    "description": (
                        "<b>Extra Abnahmestelle</b><br>\n"
                        + f"{drain['street']} {drain['city']}<br>\n"
                        + f"Abnahme: {drain['usage']} kWh<br>\n"
                    ),
                    "quantity": 1,
                    "quantity_unit": "mtl.",
                    "tax_rate": 19,
                    "single_price": 0,
                    "single_price_net": 0,
                    "single_tax_amount": 0,
                    "discount_rate": 0,
                    "discount_single_amount": 0,
                    "discount_single_price": 0,
                    "discount_single_price_net": 0,
                    "discount_single_price_net_overwrite": None,
                    "discount_single_tax_amount": 0,
                    "discount_total_amount": 0,
                    "total_price": float(settings["data"]["cloud_settings"]["consumer_base_cost"]),
                    "total_price_net": 0,
                    "total_tax_amount": 0
                })

    extra_usage_cost = (float(settings['data']['cloud_settings']['extra_kwh_cost']) / 100 * extra_usage) / 12
    offer_data["items"].append({
        "label": "",
        "description": (
            "<b>Mehrverbrauch</b><br>\n"
            + f"Geplanter Mehrverbrauch: {extra_usage} kWh<br>\n"
        ),
        "quantity": 1,
        "quantity_unit": "mtl.",
        "tax_rate": 19,
        "single_price": extra_usage_cost,
        "single_price_net": 0,
        "single_tax_amount": 0,
        "discount_rate": 0,
        "discount_single_amount": 0,
        "discount_single_price": 0,
        "discount_single_price_net": 0,
        "discount_single_price_net_overwrite": None,
        "discount_single_tax_amount": 0,
        "discount_total_amount": 0,
        "total_price": extra_usage_cost,
        "total_price_net": 0,
        "total_tax_amount": 0
    })

    for product in settings["data"]["cloud_settings"]["extra_products"]:
        if product["include_always"] == "top-one":
            offer_data = add_item_to_offer(offer.survey, offer_data, product["product_link"], product["product_folder"], 1)

    for optional_product in offer.survey.data["pv_options"]:
        if optional_product["label"] == "ZERO-Paket" and "is_selected" in optional_product and optional_product["is_selected"]:
            offer_data["items"].append({
                "label": "",
                "description": (
                    "<b>ZERO-Paket</b>"
                ),
                "quantity": 1,
                "quantity_unit": "mtl.",
                "tax_rate": 19,
                "single_price": 0,
                "single_price_net": 0,
                "single_tax_amount": 0,
                "discount_rate": 0,
                "discount_single_amount": 0,
                "discount_single_price": 0,
                "discount_single_price_net": 0,
                "discount_single_price_net_overwrite": None,
                "discount_single_tax_amount": 0,
                "discount_total_amount": 0,
                "total_price": -cloud_price,
                "total_price_net": 0,
                "total_tax_amount": 0
            })
    for product in settings["data"]["cloud_settings"]["extra_products"]:
        if product["include_always"] == "top":
            offer_data = add_item_to_offer(offer.survey, offer_data, product["product_link"], product["product_folder"], 0)

    return offer_data["items"]
