from app.models import OfferV2
from app.modules.settings.settings_services import get_one_item as get_settings

from ._utils import base_offer_data, add_item_to_offer, add_optional_item_to_offer


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
    tax_rate = 19
    cloud_price = 99
    for price in settings["data"]["cloud_settings"]["cloud_prices"]:
        if int(price["paket_range_start"]) <= int(offer.survey.data["packet_number"]) <= int(price["paket_range_end"]):
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
        + f"Durch die Cloud abgedeckter Jahresverbrauch: {total_drain} kWh<br>\n" \
        + "<small>PV, Speicher & Netzbezug</small>"
    offer_data["items"].append({
        "label": "",
        "description": (
            "<b>PV Erzeugung</b><br>\n"
            + f"Zählernummer: {offer.survey.data['current_counter_number']}<br>\n"
            + f"PV-Anlage laut Angebot: PV-{offer.id}<br>\n"
            + f"{offer.survey.data['street']} {offer.survey.data['zip']} {offer.survey.data['city']}<br>\n"
            + f"Abnahme: {offer.survey.data['pv_usage']} kWh<br>\n"
            + "Mehrverbrauch: 0 kWh<br>\n"
            + f"<small>Bei Mehrverbauch ist der Preis abhängig von der aktuellen Strompreisentwicklung derzeit {settings['data']['cloud_settings']['extra_kwh_cost']} cent / kWh</small>"
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
