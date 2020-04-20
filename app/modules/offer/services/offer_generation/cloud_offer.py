from app.models import OfferV2

from ._utils import base_offer_data, add_item_to_offer, add_optional_item_to_offer


def cloud_offer_items_by_pv_offer(offer: OfferV2):
    items = [
        {
            "label": "cCloud-Zero",
            "description": "Mit der C.Cloud.ZERO – NULL Risiko<br>Genial einfach – einfach genial<br>Die sicherste Cloud Deutschlands.<br>Stromverbrauchen, wann immer Sie ihn brauchen.",
            "quantity": 1,
            "quantity_unit": "mtl.",
            "tax_rate": 19,
            "single_price": 19.99,
            "single_price_net": 19.99 / 1.19,
            "single_tax_amount": 19.99 * 0.19,
            "discount_rate": 0,
            "discount_single_amount": 0,
            "discount_single_price": 19.99,
            "discount_single_price_net": 19.99 / 1.19,
            "discount_single_price_net_overwrite": None,
            "discount_single_tax_amount": 19.99 * 0.19,
            "discount_total_amount": 19.99,
            "total_price": 19.99,
            "total_price_net": 19.99 / 1.19,
            "total_tax_amount": 19.99 * 0.19
        }
    ]
    items[0]["description"] = items[0]["description"] + "<br>\n<br>\n"\
        + "Tarif: cCloud-Zero<br>\n" \
        + "Kündigungsfrist: 6 Monate<br>\n" \
        + "Vertragslaufzeit: 24 Monate<br>\n" \
        + "garantierte Zero-Laufzeit für (a): 10 Jahre<br>\n" \
        + f"Erwarteter Jahresverbrauch (a): {offer.survey.data['pv_usage']} kWh<br>\n"
    items.append({
        "label": "",
        "description": (
            "<b>PV Erzeugung</b><br>\n"
            + "Zählernummer:<br>\n"
            + f"PV-Anlage laut Angebot: PV-{offer.id}<br>\n"
            + "Musterstraße 1 Musterstadt<br>\n"
            + f"Abnahme: {offer.survey.data['pv_usage']} kWh<br>\n"
            + "Mehrverbrauch: 0 kWh\n"
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
    items.append({
        "label": "",
        "description": (
            "<b>Abnahmestelle</b><br>\n"
            + "Zählernummer:<br>\n"
            + "Musterstraße 1 Musterstadt<br>\n"
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
        "total_price": 12,
        "total_price_net": 0,
        "total_tax_amount": 0
    })
    return items
