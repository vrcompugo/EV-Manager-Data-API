import datetime
import random

from app import db
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict
from app.modules.email.email_services import generate_email, send_email
from app.modules.settings.settings_services import get_one_item as get_settings

from .models.lead import Lead, LeadSchema
from .models.lead_comment import LeadComment
from .models.lead_activity import LeadActivity


def add_item(data):
    new_item = Lead()
    if "datetime" in data:
        data["last_status_update"] = data["datetime"]
    else:
        data["last_status_update"] = datetime.datetime.now()
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
    db.session.flush()
    db.session.commit()
    return new_item


def update_item(id, data):
    item = db.session.query(Lead).get(id)
    if item is not None:
        if "status" in data and item.status != data["status"]:
            data["last_status_update"] = datetime.datetime.now()
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
    if "activities" in data:
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


def send_welcome_email(lead):
    from .lead_comment_services import add_item as add_comment_item

    if lead is None or lead.customer is None:
        raise ApiException("item_doesnt_exist", "Item doesn't exist.", 409)

    existing_comment = LeadComment.query\
        .filter(LeadComment.lead_id == lead.id)\
        .filter(LeadComment.code == "welcome_email").first()
    if existing_comment is not None:
        return False

    if lead.customer.email is None or lead.customer.email == "":
        add_comment_item({
            "lead_id": lead.id,
            "user_id": None,
            "change_to_offer_created": False,
            "code": "welcome_email",
            "automated": True,
            "comment": "Achtung!!!: Automatischer Versand der Willkommens E-Mail an fehlgeschlagen, "
                       "da keine E-Mail angegeben ist"
        })
        return False

    schema = LeadSchema()
    email = generate_email("lead_welcome_email", schema.dump(lead, many=False))
    email.recipients = [lead.customer.email]
    email = send_email(email=email)
    if email.status == "sent":
        comment = "Automatische Willkommens E-Mail versendet an {}".format(lead.customer.email)
    else:
        comment = "Achtung!!!: Automatischer Versand der Willkommens E-Mail an {} fehlgeschlagen.\nFehler: {}".format(lead.customer.email, email.status)

    add_comment_item({
        "lead_id": lead.id,
        "user_id": None,
        "change_to_offer_created": False,
        "code": "welcome_email",
        "automated": True,
        "comment": comment
    })

    return True
