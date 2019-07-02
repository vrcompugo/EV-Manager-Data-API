import datetime

from app import db
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict

from .models.pv_system import PVSystem, PVSystemSchema


def add_item(data):
    new_item = PVSystem()
    new_item = set_attr_by_dict(new_item, data, ["id"])
    db.session.add(new_item)
    db.session.commit()
    return new_item


def update_item(id, data):
    item = db.session.query(PVSystem).get(id)
    if item is not None:
        item = set_attr_by_dict(item, data, ["id"])
        db.session.commit()
        return item
    else:
        raise ApiException("item_doesnt_exist", "Item doesn't exist.", 409)


def get_items(tree, sort, offset, limit, fields):
    return get_items_by_model(PVSystem, PVSystemSchema, tree, sort, offset, limit, fields)


def get_one_item(id, fields = None):
    return get_one_item_by_model(PVSystem, PVSystemSchema, id, fields, [db.subqueryload("role")])

