
from app.models import Order
from ..add_update_item import add_item_v2
from ._utils import base_offer_data, add_item_to_offer, add_optional_item_to_offer


def enpal_offer_by_order(order: Order):
    offer = None
    offer_data = base_offer_data("enpal-offer", order=order)
    if "usage_without_pv" not in order.data or order.data["usage_without_pv"] == "":
        print("no usage information")
        return offer

    if order.data["usage_without_pv"] == "bis 3900 kWh":
        offer_data = add_item_to_offer(
            offer_data=offer_data,
            product_name="Speicher Li 2,5",
            product_folder="ENPAL - Speicher Nachrüstung Enpal Kunden",
            quantity=1)
    if order.data["usage_without_pv"] == "bis 6000 kWh":
        offer_data = add_item_to_offer(
            offer_data=offer_data,
            product_name="SENEC 5.0 Li",
            product_folder="ENPAL - Speicher Nachrüstung Enpal Kunden",
            quantity=1)
    if order.data["usage_without_pv"] == "bis 8000 kWh":
        offer_data = add_item_to_offer(
            offer_data=offer_data,
            product_name="SENEC Home 7,5",
            product_folder="ENPAL - Speicher Nachrüstung Enpal Kunden",
            quantity=1)
    if order.data["usage_without_pv"] == "über 8000 kWh":
        offer_data = add_item_to_offer(
            offer_data=offer_data,
            product_name="SENEC Home 10.0 Li",
            product_folder="ENPAL - Speicher Nachrüstung Enpal Kunden",
            quantity=1)
    offer_data = add_item_to_offer(
        offer_data=offer_data,
        product_name="Options Paket SENEC",
        product_folder="ENPAL - Speicher Nachrüstung Enpal Kunden",
        quantity=0)
    offer_data = add_item_to_offer(
        offer_data=offer_data,
        product_name="Notstrom",
        product_folder="ENPAL - Speicher Nachrüstung Enpal Kunden",
        quantity=0)
    offer_data = add_item_to_offer(
        offer_data=offer_data,
        product_name="Service S.pro",
        product_folder="ENPAL - Speicher Nachrüstung Enpal Kunden",
        quantity=0)

    offer = add_item_v2(offer_data)
    return offer
