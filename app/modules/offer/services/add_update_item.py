import datetime

from app import db
from app.models import Offer, OfferV2, OfferV2Item
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
    # loading relations for pdf creation
    customer = new_item.customer
    items = new_item.items
    address = new_item.address
    return new_item


def update_item_v2(id, data):
    item = db.session.query(OfferV2).get(id)
    if item is None:
        raise ApiException("item_doesnt_exist", "Item doesn't exist.", 409)
    item = set_attr_by_dict(item, data, ["id", "items"])
    if "items" in data:
        item.items = []
        for item_data in data["items"]:
            item_object = OfferV2Item()
            item_object = set_attr_by_dict(item_object, item_data, ["id"])
            item.items.append(item_object)
    db.session.commit()
    # loading relations for pdf creation
    customer = new_item.customer
    items = new_item.items
    address = new_item.address
    return item
