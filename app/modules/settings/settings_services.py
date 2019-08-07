import datetime

from app import db
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict

from .models.settings import Settings, SettingsSchema


def add_item(data):
    item = db.session.query(Settings).filter(Settings.section == data["section"]).first()
    if item is not None:
        return None
    new_item = Settings()
    new_item = set_attr_by_dict(new_item, data, ["id"])
    db.session.add(new_item)
    db.session.commit()
    return new_item


def update_item(section, data):
    item = db.session.query(Settings).filter(Settings.section == section).first()
    if item is not None:
        updated_item = set_attr_by_dict(item, data, ["id"])
        db.session.commit()
        return updated_item
    else:
        raise ApiException("item_doesnt_exist", "Item doesn't exist.", 409)


def get_items(tree, sort, offset, limit, fields):
    return get_items_by_model(Settings, SettingsSchema, tree, sort, offset, limit, fields)


def get_one_item(section, fields = None, options = None):
    if fields is None:
        fields = "_default_"
    query = Settings.query
    if options is not None:
        query = query.options(*options)
    item = query.filter(Settings.section == section).first()
    if item is None:
        return None
    fields = fields.split(",")
    item_schema = SettingsSchema()
    data = item_schema.dump(item, many=False).data
    if fields[0] != "_default_":
        data_filtered = {}
        for field in fields:
            field = field.strip()
            if field in data:
                data_filtered[field] = data[field]
        data = data_filtered
    return data

