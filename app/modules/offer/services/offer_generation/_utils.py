import datetime
import json

from app.models import Survey, Product


def base_offer_data(offer_group, survey=None, order=None):
    data = {
        "offer_group": offer_group,
        "datetime": datetime.datetime.now(),
        "currency": "eur",
        "tax_rate": 19,
        "subtotal": 0,
        "subtotal_net": 0,
        "shipping_cost": 0,
        "shipping_cost_net": 0,
        "discount_total": 0,
        "total_tax": 0,
        "total": 0,
        "status": "created",
        "items": []
    }
    if survey is not None:
        data["customer_id"] = survey.customer_id
        data["address_id"] = survey.customer.default_address_id
        data["payment_account_id"] = survey.customer.default_payment_account_id
        data["reseller_id"] = survey.reseller_id
        data["survey_id"] = survey.id
    if order is not None:
        data["customer_id"] = order.customer_id
        data["address_id"] = order.customer.default_address_id
        data["payment_account_id"] = order.customer.default_payment_account_id
        data["reseller_id"] = order.reseller_id
    return data


def add_item_to_offer(survey=None, offer_data=None, product_name=None, product_folder=None, quantity=None, position="top", packet_number=None):
    if packet_number is None:
        packet_number = int(survey.data["packet_number"])
    product = None
    if survey is not None:
        product = Product.query\
            .filter(Product.name == product_name)\
            .filter(Product.product_group == product_folder)\
            .filter(Product.packet_range_start <= packet_number)\
            .filter(Product.packet_range_end >= packet_number)\
            .first()
    if product is None:
        product = Product.query\
            .filter(Product.name == product_name)\
            .filter(Product.product_group == product_folder)\
            .first()
    if product is None:
        print("Product not found: {}".format(product_name))
        return offer_data
    tax_rate = 19
    single_price = round(float(product.price_net) * (1 + tax_rate / 100), 4)
    single_price_net = float(product.price_net)
    single_tax_amount = single_price - single_price_net
    quantity_unit = product.pack_unit
    if offer_data["offer_group"] == "heater-offer-con" and product_name.find("AIO Paket") == -1:
        single_price = single_price / 1000 * 7.9
        single_price_net = single_price_net / 1000 * 7.9
        single_tax_amount = single_tax_amount / 1000 * 7.9
        quantity_unit = "mtl."
    item_data = {
        "product_id": product.id,
        "sort": 0,
        "number": product.number,
        "label": product.name,
        "description": product.description,
        "position": position,
        "quantity_unit": quantity_unit,
        "weight_single": 0,
        "weight_total": 0,
        "quantity": quantity,
        "cost": 0,
        "tax_rate": 19,
        "single_price": single_price,
        "single_price_net": single_price_net,
        "single_tax_amount": single_tax_amount,
        "discount_rate": 0,
        "discount_single_amount": 0,
        "discount_single_price": single_price,
        "discount_single_price_net": single_price_net,
        "discount_single_tax_amount": single_tax_amount,
        "total_price": quantity * single_price,
        "total_price_net": quantity * single_price_net,
        "total_tax_amount": quantity * single_tax_amount
    }
    offer_data["subtotal"] = offer_data["subtotal"] + item_data["total_price"]
    offer_data["subtotal_net"] = offer_data["subtotal_net"] + item_data["total_price_net"]
    offer_data["total_tax"] = offer_data["total_tax"] + item_data["total_tax_amount"]
    offer_data["total"] = offer_data["total"] + item_data["total_price"]
    offer_data["items"].append(item_data)
    return offer_data


def add_optional_item_to_offer(survey: Survey, offer_data, optional_product):
    quantity = 0
    if "is_selected" in optional_product and optional_product["is_selected"]:
        quantity = 1
    include_always = "top"
    if "include_always" in optional_product:
        include_always = optional_product["include_always"]
    if "has_options" in optional_product and optional_product["has_options"]:
        for option in optional_product["options"]:
            if "is_selected" in option and option["is_selected"] is True:
                return add_item_to_offer(
                    survey,
                    offer_data,
                    option["product_link"],
                    option["product_folder"],
                    quantity,
                    include_always
                )
    if "has_special_packet_variants" in optional_product and optional_product["has_special_packet_variants"]:
        for option in optional_product["variants"]:
            if int(option["paket_range_start"]) <= int(survey.data["packet_number"]) <= int(option["paket_range_end"]):
                return add_item_to_offer(
                    survey,
                    offer_data,
                    option["product_link"],
                    option["product_folder"],
                    quantity,
                    include_always
                )
    return add_item_to_offer(
        survey,
        offer_data,
        optional_product["product_link"],
        optional_product["product_folder"],
        quantity,
        include_always
    )
