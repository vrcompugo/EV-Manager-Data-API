import datetime

from app import db
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict

from .models.order import Order, OrderSchema


def add_item(data):
    new_item = Order()
    new_item = set_attr_by_dict(new_item, data, ["id"])
    new_item.last_updated = datetime.datetime.now()
    db.session.add(new_item)
    db.session.commit()
    return new_item


def update_item(id, data):
    item = db.session.query(Order).get(id)
    if item is not None:
        item = set_attr_by_dict(item, data, ["id"])
        db.session.commit()
        return item
    else:
        raise ApiException("item_doesnt_exist", "Item doesn't exist.", 409)


def commission_calulation(order: Order):
    if order is None or order.reseller is None:
        return None
    if order.commissions is None:
        return order
    is_external = order.reseller.min_commission is None or float(order.reseller.min_commission) <= 0
    for commission in order.commissions:
        if commission["type"] == "PV":
            commission["provision_rate"] = 0
            if commission["discount_range"] == "0%":
                commission["provision_rate"] = 10 if is_external else 6
            if commission["discount_range"] == "bis 5%":
                commission["provision_rate"] = 8.5 if is_external else 5
            if commission["discount_range"] == "bis 8%":
                commission["provision_rate"] = 7.5 if is_external else 4.25
                print("asd", commission["provision_rate"])
            if commission["discount_range"] == "bis 10%":
                commission["provision_rate"] = 6.5 if is_external else 3.75
            if commission["discount_range"] == "bis 15%":
                commission["provision_rate"] = 5 if is_external else 3
            if commission["discount_range"] == "bis 20%":
                commission["provision_rate"] = 3 if is_external else 2
            if commission["discount_range"] in ["manuell", "Sondervereinbarung"]:
                commission["provision_rate"] = 4 if is_external else 2.5
            commission["provision_net"] = \
                round(commission["value_net"] * (commission["provision_rate"] / 100), 2)
            if "options" in commission and type(commission["options"]) == list:
                for option in commission["options"]:
                    if option["key"] == "Wärmepumpe (ecoStar)":
                        option["value_net"] = 250 if is_external else 200
                        commission["provision_net"] = commission["provision_net"] + option["value_net"]
        if "provision_net" in commission:
            order.commission_value_net = float(order.commission_value_net) + commission["provision_net"]
    print(is_external)
    return order


def get_items(tree, sort, offset, limit, fields):
    return get_items_by_model(Order, OrderSchema, tree, sort, offset, limit, fields)


def generate_contract_number(order: Order):
    if order.category != "Cloud Verträge":
        return None
    if order.contract_number not in [None, "", "X"]:
        return order.contract_number
    customer_counter = 300000 + order.id
    customer_number_prefix = "C" + order.datetime.strftime("%y%m")
    return f"{customer_number_prefix}{customer_counter}"
