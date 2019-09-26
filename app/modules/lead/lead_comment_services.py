import datetime
import random

from app import db
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict
from app.modules.importer.sources.nocrm_io.lead_comment import update_lead_comment

from .models.lead_comment import LeadComment, LeadCommentSchema


def add_item(data):
    if datetime not in data:
        data["datetime"] = datetime.datetime.now()
    new_item = LeadComment()
    new_item = set_attr_by_dict(new_item, data, ["id"])
    db.session.add(new_item)
    db.session.commit()
    new_item.status_code = update_lead_comment(new_item)
    return new_item


def update_item(id, data):
    item = db.session.query(LeadComment).get(id)
    if item is not None:
        item = set_attr_by_dict(item, data, ["id"])
        db.session.commit()
        update_lead_comment(item)
        return item
    else:
        raise ApiException("item_doesnt_exist", "Item doesn't exist.", 409)


def get_items(tree, sort, offset, limit, fields):
    return get_items_by_model(LeadComment, LeadCommentSchema, tree, sort, offset, limit, fields)


def get_one_item(id, fields = None):
    return get_one_item_by_model(LeadComment, LeadCommentSchema, id, fields)

