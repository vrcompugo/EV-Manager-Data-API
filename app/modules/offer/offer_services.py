import datetime

from app import db
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict
from app.models import Lead, Product

from .models.offer import Offer, OfferSchema
from .models.offer_v2 import OfferV2
from .models.offer_v2_item import OfferV2Item


def add_item(data):
    new_item = Offer()
    new_item = set_attr_by_dict(new_item, data, ["id"])
    new_item.last_updated = datetime.datetime.now()
    db.session.add(new_item)
    db.session.commit()
    return new_item


def update_item(id, data):
    item = db.session.query(Offer).get(id)
    if item is not None:
        item = set_attr_by_dict(item, data, ["id"])
        db.session.commit()
        return item
    else:
        raise ApiException("item_doesnt_exist", "Item doesn't exist.", 409)


def add_item_v2(data):
    new_item = OfferV2()
    new_item = set_attr_by_dict(new_item, data, ["id", "items"])
    if "items" in data:
        new_item.items = []
        for item_data in data["items"]:
            item_object = OfferV2Item()
            item_object = set_attr_by_dict(item_object, item_data, ["id"])
            new_item.items.append(item_object)
    new_item.last_updated = datetime.datetime.now()
    db.session.add(new_item)
    db.session.commit()
    return new_item


def get_items(tree, sort, offset, limit, fields):
    return get_items_by_model(Offer, OfferSchema, tree, sort, offset, limit, fields)


def get_one_item(id, fields = None):
    return get_one_item_by_model(Offer, OfferSchema, id, fields, [])


def automatic_offer_creation_by_survey(survey, old_data=None):
    if ("offer_comment" not in survey.data or survey.data["offer_comment"] == "") and \
            survey.data["pv_usage"] is not None and \
            survey.data["pv_usage"] != "" and \
            int(survey.data["pv_usage"]) > 0 and \
            (old_data is None or survey.data["pv_usage"] != old_data["data"]["pv_usage"]):
        if survey.data["pv_module_type"] == "390":
            product_name = "Paket {} (390)".format(survey.data["packet_number"])
        else:
            product_name = "PV Paket {}".format(survey.data["packet_number"])
        product = Product.query.filter(Product.name == product_name).first()
        if product is None:
            return None
        tax_rate = 19
        single_price = round(float(product.price_net) * (1 + tax_rate/100), 4)
        single_price_net = float(product.price_net)
        single_tax_amount = single_price - single_price_net
        data = {
            "customer_id": survey.customer_id,
            "address_id": survey.customer.default_address_id,
            "payment_account_id": survey.customer.default_payment_account_id,
            "reseller_id": survey.reseller_id,
            "survey_id": survey.id,
            "offer_group": "pv-offer",
            "datetime": datetime.datetime.now(),
            "currency": "eur",
            "tax_rate": tax_rate,
            "subtotal": single_price,
            "subtotal_net": single_price_net,
            "shipping_cost": 0,
            "shipping_cost_net": 0,
            "discount_total": 0,
            "total_tax": single_tax_amount,
            "total": single_price,
            "status": "created",
            "items": [
                {
                    "product_id": product.id,
                    "sort": 0,
                    "number": product.number,
                    "label": product.name,
                    "description": "",
                    "weight_single": 0,
                    "weight_total": 0,
                    "quantity": 1,
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
                    "total_price": single_price,
                    "total_price_net": single_price_net,
                    "total_tax_amount": single_tax_amount
                }
            ]
        }
        lead = Lead.query.filter(Lead.customer_id == survey.customer.id).first()
        if lead is not None:
            data["lead_id"] = lead.id
        offer = add_item_v2(data)

