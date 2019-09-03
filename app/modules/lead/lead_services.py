import datetime
import random

from app import db
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict
from app.modules.settings.settings_services import get_one_item as get_settings

from .models.lead import Lead, LeadSchema
from .models.lead_activity import LeadActivity


def add_item(data):
    new_item = Lead()
    new_item = set_attr_by_dict(new_item, data, ["id", "activities"])
    settings = get_settings("leads")
    if settings is not None and "static_file_attachments" in settings["data"]:
        attachments = []
        for attachment in settings["data"]["static_file_attachments"]:
            attachment["fixed"] = True
            attachments.append(attachment)
        new_item.attachments = attachments
        new_item.activities = generate_activity_list(data)
    db.session.add(new_item)
    db.session.commit()
    return new_item


def update_item(id, data):
    item = db.session.query(Lead).get(id)
    if item is not None:
        item = set_attr_by_dict(item, data, ["id", "activities"])
        settings = get_settings("leads")
        if settings is not None and "static_file_attachments" in settings["data"]:
            attachments = []
            for attachment in settings["data"]["static_file_attachments"]:
                attachment["fixed"] = True
                attachments.append(attachment)
            item.attachments = attachments
        item.activities = generate_activity_list(data)
        db.session.commit()
        return item
    else:
        raise ApiException("item_doesnt_exist", "Item doesn't exist.", 409)


def generate_activity_list(data):
    activities = []
    for activity in data["activities"]:
        if "id" in activity and activity["id"] > 0:
            activity_item = db.session.query(LeadActivity).filter(LeadActivity.id == activity["id"]).first()
            if activity_item is not None:
                activity_item = set_attr_by_dict(activity_item, activity, ["id"])
                activities.append(activity_item)
        else:
            activity_item = LeadActivity()
            activity_item = set_attr_by_dict(activity_item, activity, ["id"])
            activities.append(activity_item)
    return activities


def get_items(tree, sort, offset, limit, fields):
    return get_items_by_model(Lead, LeadSchema, tree, sort, offset, limit, fields)


def get_one_item(id, fields = None):
    return get_one_item_by_model(Lead, LeadSchema, id, fields)

