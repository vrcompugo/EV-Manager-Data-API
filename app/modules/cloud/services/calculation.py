import math
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

    result = {
        "lightcloud_extra_price_per_kwh": settings["data"]["cloud_settings"]["lightcloud_extra_price_per_kwh"],
        "heatcloud_extra_price_per_kwh": settings["data"]["cloud_settings"]["heatcloud_extra_price_per_kwh"],
        "ecloud_extra_price_per_kwh": settings["data"]["cloud_settings"]["ecloud_extra_price_per_kwh"],
        "consumercloud_extra_price_per_kwh": settings["data"]["cloud_settings"]["lightcloud_extra_price_per_kwh"],
        "errors": [],
        "invalid_form": False,
        "kwp_extra": 0,
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
        "cloud_price_heatcloud": 0,
        "cloud_price_ecloud": 0,
        "cloud_price_emove": 0,
        "cloud_price_consumer": 0,
        "user_one_time_cost": 0,
        "power_usage": 0,
        "heater_usage": 0,
        "ecloud_usage": 0,
        "consumer_usage": 0,
        "conventional_price_light": 0,
        "conventional_price_heatcloud": 0,
        "conventional_price_ecloud": 0
    }
    if "pv_kwp" in data:
        data["pv_kwp"] = float(data["pv_kwp"])
    else:
        data["pv_kwp"] = 0
    direction_factor = 1
    if "roof_direction" in data:
        if data["roof_direction"] == "north":
            direction_factor = 1.15
        if data["roof_direction"] == "south":
            direction_factor = 0.9

    if "power_usage" in data and data["power_usage"] != "" and data["power_usage"] != "0" and data["power_usage"] != 0:
        data["power_usage"] = int(data["power_usage"])
        result["power_usage"] = data["power_usage"]
        result["min_kwp_light"] = data["power_usage"] * settings["data"]["cloud_settings"]["power_to_kwp_factor"] * direction_factor / 1000
        result["storage_size"] = round((data["power_usage"] / 500)) * 500 / 1000
        result["cloud_price_light"] = result["cloud_price_light"] + list(filter(
            lambda item: item['from'] <= data["power_usage"] and data["power_usage"] <= item['to'],
            settings["data"]["cloud_settings"]["cloud_user_prices"][str(user["id"])]
        ))[0]["value"]
        result["conventional_price_light"] = (data["power_usage"] * settings["data"]["cloud_settings"]["lightcloud_conventional_price_per_kwh"]) / 12

    if "heater_usage" in data and data["heater_usage"] != "" and data["heater_usage"] != "0" and data["heater_usage"] != 0:
        data["heater_usage"] = int(data["heater_usage"])
        result["heater_usage"] = data["heater_usage"]
        heater_to_kwp_factor = list(filter(
            lambda item: item['from'] <= data["heater_usage"] and data["heater_usage"] <= item['to'],
            settings["data"]["cloud_settings"]["heater_to_kwp_factor"]
        ))[0]["value"]
        result["cloud_price_heatcloud"] = list(filter(
            lambda item: item['from'] <= data["heater_usage"] and data["heater_usage"] <= item['to'],
            settings["data"]["cloud_settings"]["cloud_user_heater_prices"][str(user["id"])]
        ))[0]["value"]
        result["min_kwp_heatcloud"] = data["heater_usage"] * heater_to_kwp_factor * direction_factor / 1000
        result["conventional_price_heatcloud"] = (data["heater_usage"] * settings["data"]["cloud_settings"]["heatcloud_conventional_price_per_kwh"]) / 12

    if "ecloud_usage" in data and data["ecloud_usage"] != "" and data["ecloud_usage"] != "0" and data["ecloud_usage"] != 0:
        data["ecloud_usage"] = int(data["ecloud_usage"])
        result["ecloud_usage"] = data["ecloud_usage"]
        result["cloud_price_ecloud"] = settings["data"]["cloud_settings"]["cloud_user_ecloud_prices"][str(user["id"])]
        result["min_kwp_ecloud"] = data["ecloud_usage"] / settings["data"]["cloud_settings"]["ecloud_to_kwp_factor"]
        result["conventional_price_ecloud"] = (data["ecloud_usage"] * settings["data"]["cloud_settings"]["ecloud_conventional_price_per_kwh"]) / 12

    if "consumers" in data:
        consumer_usage = 0
        for consumer in data["consumers"]:
            consumer_usage = consumer_usage + int(consumer["usage"])
            consumer_price = list(filter(
                lambda item: item['from'] <= int(consumer["usage"]) and int(consumer["usage"]) <= item['to'],
                settings["data"]["cloud_settings"]["cloud_user_consumer_prices"][str(user["id"])]
            ))
            if len(consumer_price) > 0:
                result["cloud_price_consumer"] = result["cloud_price_consumer"] + consumer_price[0]["value"]
        result["consumer_usage"] = consumer_usage
        result["min_kwp_consumer"] = (consumer_usage * settings["data"]["cloud_settings"]["consumer_to_kwp_factor"] * direction_factor) / 1000

    if "emove_tarif" in data:
        if data["emove_tarif"] in settings["data"]["cloud_settings"]["cloud_emove"]:
            result["min_kwp_emove"] = settings["data"]["cloud_settings"]["cloud_emove"][data["emove_tarif"]]["kwp"]
            result["cloud_price_emove"] = settings["data"]["cloud_settings"]["cloud_emove"][data["emove_tarif"]]["price"]

    if "price_guarantee" in data:
        if str(user["id"]) in settings["data"]["cloud_settings"]["cloud_guarantee"]:
            if data["price_guarantee"] in settings["data"]["cloud_settings"]["cloud_guarantee"][str(user["id"])]:
                result["user_one_time_cost"] = result["user_one_time_cost"] + settings["data"]["cloud_settings"]["cloud_guarantee"][str(user["id"])][data["price_guarantee"]]["price"]

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

    if data["pv_kwp"] > 0:
        result["kwp_extra"] = data["pv_kwp"] - result["min_kwp"]
        if result["kwp_extra"] > 0:
            result["cloud_price_extra"] = -1 * result["kwp_extra"] * settings["data"]["cloud_settings"]["kwp_to_refund_factor"]
        if result["kwp_extra"] < 0:
            max_kwp = (result["min_kwp_light"]
                       + result["min_kwp_heatcloud"]
                       + result["min_kwp_ecloud"]
                       + result["min_kwp_consumer"])
            extra_kwh_ratio = 1 - (data["pv_kwp"] - result["min_kwp_emove"]) / max_kwp
            result["cloud_price_extra"] = (
                ((result["min_kwp_light"] / max_kwp) * result["power_usage"] * extra_kwh_ratio * result["lightcloud_extra_price_per_kwh"]) / 12
                + ((result["min_kwp_heatcloud"] / max_kwp) * result["heater_usage"] * extra_kwh_ratio * result["heatcloud_extra_price_per_kwh"]) / 12
                + ((result["min_kwp_ecloud"] / max_kwp) * result["ecloud_usage"] * extra_kwh_ratio * result["ecloud_extra_price_per_kwh"]) / 12
                + ((result["min_kwp_consumer"] / max_kwp) * result["consumer_usage"] * extra_kwh_ratio * result["consumercloud_extra_price_per_kwh"]) / 12
            )

    result["cloud_price"] = (result["cloud_price_light"]
                             + result["cloud_price_heatcloud"]
                             + result["cloud_price_ecloud"]
                             + result["cloud_price_consumer"]
                             + result["cloud_price_emove"])

    result["conventional_price"] = (result["conventional_price_light"]
                                    + result["conventional_price_heatcloud"]
                                    + result["conventional_price_ecloud"])

    result["max_kwp"] = result["min_kwp"] + result["kwp_extra"]
    result["cloud_price_incl_refund"] = result["cloud_price"] + result["cloud_price_extra"]

    if "cloud_price_wish" in data and data["cloud_price_wish"] != "" and data["cloud_price_wish"] != "0" and data["cloud_price_wish"] != 0:
        if result["cloud_price_incl_refund"] > float(data["cloud_price_wish"]) > 0 and "price_guarantee" in data and data["price_guarantee"] == "2_years":
            price_diff = result["cloud_price_incl_refund"] - float(data["cloud_price_wish"])
            result["user_one_time_cost"] = result["user_one_time_cost"] + (result["cloud_price_incl_refund"] - float(data["cloud_price_wish"])) * 24

    return result


def get_cloud_products(data=None, offer=None):
    settings = get_settings("pv-settings")
    if settings is None:
        return None
    tax_rate = 16
    offer_data = {}
    wish_price = False
    pv_production = (
        "<b>PV Erzeugung</b><br>\n"
        + f"PV-Anlage mit mindestens: {numberformat(float(data['calculated']['min_kwp']), digits=2)}kWp<br>\n"
    )
    if "pv_kwp" in data['data'] and data['data']["pv_kwp"] > 0:
        pv_production = (
            "<b>PV Erzeugung</b><br>\n"
            + f"PV-Anlage mindestens zu verbauen: {numberformat(float(data['calculated']['min_kwp']), digits=2)}kWp<br>\n"
            + f"PV-Anlage wird verbaut: {numberformat(float(data['data']['pv_kwp']), digits=2)}kWp<br>\n"
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
    cloud_description = "Mit der C.Cloud.ZERO – NULL Risiko<br>Genial einfach – einfach genial<br>Die sicherste Cloud Deutschlands.<br>Stromverbrauchen, wann immer Sie ihn brauchen."
    cloud_tarif = "cCloud-Zero"
    if "document_style" in data["data"]:
        if data["data"]["document_style"] == "bsh":
            cloud_label = "BSH-Cloud"
            cloud_description = "Genial einfach – einfach genial<br>Stromverbrauchen, wann immer Sie ihn brauchen."
            cloud_tarif = "BSH-Cloud"
        if data["data"]["document_style"] == "eeg":
            cloud_label = "EEG-Cloud"
            logo = render_template("offer/logo-eeg.html")
            cloud_description = f"<div style='float: right'>{logo}</div>Genial einfach – einfach genial<br>Stromverbrauchen, wann immer Sie ihn brauchen."
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
        + f"Durch die Cloud abgedeckter Jahresverbrauch: {light_cloud_usage} kWh<br>\n" \
        + "<small>PV, Speicher & Netzbezug</small><br>\n" \
        + f"<small>Bei Mehrverbauch ist der Preis abhängig von der aktuellen Strompreisentwicklung derzeit {numberformat(lightcloud_extra_price_per_kwh * 100, digits=2)} cent / kWh</small>"
    offer_data["items"].append(monthly_price_product_base(
        description=pv_production,
        single_price=0))
    if data["calculated"]["cloud_price_heatcloud"] > 0:
        offer_data["items"].append(monthly_price_product_base(
            description=("<b>Wärmecloud</b><br>"
                         + f"Durch die Cloud abgedeckter Jahresverbrauch: {data['calculated']['heater_usage']} kWh<br>\n"
                         + f"<small>Bei Mehrverbauch ist der Preis abhängig von der aktuellen Strompreisentwicklung derzeit {numberformat(data['calculated']['heatcloud_extra_price_per_kwh'] * 100, digits=2)} cent / kWh</small>"),
            single_price=(0 if wish_price else data["calculated"]["cloud_price_heatcloud"])))
    if data["calculated"]["cloud_price_ecloud"] > 0:
        offer_data["items"].append(monthly_price_product_base(
            description=("<b>eCloud</b><br>"
                         + f"Durch die Cloud abgedeckter Jahresverbrauch: {data['calculated']['ecloud_usage']} kWh<br>\n"
                         + f"<small>Bei Mehrverbauch ist der Preis abhängig von der aktuellen Strompreisentwicklung derzeit {numberformat(data['calculated']['ecloud_extra_price_per_kwh'] * 100, digits=2)} cent / kWh</small>"),
            single_price=(0 if wish_price else data["calculated"]["cloud_price_ecloud"])))
    if data["calculated"]["cloud_price_consumer"] > 0:
        offer_data["items"].append(monthly_price_product_base(
            description=("<b>Consumer</b><br>"
                         + f"Durch die Cloud abgedeckter Jahresverbrauch: {data['calculated']['consumer_usage']} kWh<br>\n"
                         + f"<small>Bei Mehrverbauch ist der Preis abhängig von der aktuellen Strompreisentwicklung derzeit {numberformat(data['calculated']['consumercloud_extra_price_per_kwh'] * 100, digits=2)} cent / kWh</small>"),
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
    if "zero_option" in data["data"] and data["data"]["zero_option"] is True:
        offer_data["items"].append(monthly_price_product_base(
            description="<b>ZERO-Paket</b>",
            single_price=-cloud_price))
    offer_data["items"].append(monthly_price_product_base(
        description="<b>Cashback</b><br>Wird weniger Strom verbraucht als bei (a) vereinbart,<br>So erhälten Sie 10cent inkl. mwst als Energiespar-Bonus von uns zurück.<br>Die ersten 250kwh bleiben davon ausgenommen.",
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
    if "has_heatcloud" in offer.survey.data and offer.survey.data["has_heatcloud"] and "heatcloud_usage" in offer.survey.data:
        data["heater_usage"] = offer.survey.data["heatcloud_usage"]
    if "has_ecloud" in offer.survey.data and offer.survey.data["has_ecloud"] and "ecloud_usage" in offer.survey.data:
        data["ecloud_usage"] = offer.survey.data["ecloud_usage"]
    if "cloud_emove" in offer.survey.data:
        data["emove_tarif"] = offer.survey.data["cloud_emove"]
    if "has_extra_drains" in offer.survey.data and offer.survey.data["has_extra_drains"]:
        for drain in offer.survey.data["extra_drains"]:
            if "usage" in drain and drain["usage"] != "":
                data["consumers"].append(drain)
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
            if "usage" in drain and drain["usage"] != "":
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
    taxrate = 16
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