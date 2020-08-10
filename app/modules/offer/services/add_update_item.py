import datetime

from app import db
from app.models import Offer, OfferV2, OfferV2Item
from app.modules.customer.services.customer_services import add_item as add_customer
from app.utils.set_attr_by_dict import set_attr_by_dict
from app.exceptions import ApiException


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
    if "customer_raw" in data:
        data["customer_raw"]["UPDATE_IF_EXISTS"] = True
        customer = add_customer(data["customer_raw"])
        if customer is not None:
            data["customer_id"] = customer.id
            if customer.default_address is not None:
                data["address_id"] = customer.default_address.id
    new_item = OfferV2()
    new_item = set_attr_by_dict(new_item, data, ["id", "items", "customer_raw"])
    if "items" in data:
        new_item.items = []
        for item_data in data["items"]:
            item_object = OfferV2Item()
            item_object = set_attr_by_dict(item_object, item_data, ["id"])
            new_item.items.append(item_object)
    new_item.last_updated = datetime.datetime.now()
    db.session.add(new_item)
    db.session.commit()
    new_item.number = new_item.number_prefix + str(new_item.id)
    db.session.commit()
    # loading relations for pdf creation
    customer = new_item.customer
    items = new_item.items
    address = new_item.address
    return new_item


def update_item_v2(id, data):
    if "customer_raw" in data:
        data["customer_raw"]["UPDATE_IF_EXISTS"] = True
        customer = add_customer(data["customer_raw"])
        if customer is not None:
            data["customer_id"] = customer.id
            data["address_id"] = customer.default_address.id
    item = db.session.query(OfferV2).get(id)
    if item is None:
        raise ApiException("item_doesnt_exist", "Item doesn't exist.", 409)
    item = set_attr_by_dict(item, data, ["id", "items", "customer_raw"])
    if "items" in data:
        item.items = []
        for item_data in data["items"]:
            item_object = OfferV2Item()
            item_object = set_attr_by_dict(item_object, item_data, ["id"])
            item.items.append(item_object)
    db.session.commit()
    # loading relations for pdf creation
    customer = item.customer
    items = item.items
    address = item.address
    return item
