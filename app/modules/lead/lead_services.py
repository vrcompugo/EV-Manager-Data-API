import datetime
import random

from app import db
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict
from app.modules.email.email_services import generate_email, send_email
from app.modules.settings.settings_services import get_one_item as get_settings
from app.modules.events.event_services import add_trigger
from app.models import Reseller

from .models.lead import Lead, LeadSchema
from .models.lead_comment import LeadComment
from .models.lead_activity import LeadActivity


def add_item(data):
    new_item = Lead()
    if "datetime" in data:
        data["last_status_update"] = data["datetime"]
    else:
        data["last_status_update"] = datetime.datetime.now()
    while "number" not in data or data["number"] is None or data["number"] == "":
        data["number"] = str(random.randint(100000, 999999))
        existing = db.session.query(Lead).filter(Lead.number == data["number"]).first()
        if existing is not None:
            data["number"] = None
    data["last_update"] = datetime.datetime.now()
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
    if new_item.customer is not None:
        new_item.customer.lead_number = new_item.number
        new_item.customer.reseller_id = new_item.reseller_id
    db.session.commit()
    return new_item


def update_item(id, data):
    item = db.session.query(Lead).get(id)
    if item is not None:
        if item.number is None or item.number == "":
            while "number" not in data or data["number"] is None or data["number"] == "":
                item.number = str(random.randint(100000, 999999))
                existing = db.session.query(Lead).filter(Lead.number == data["number"]).first()
                if existing is not None:
                    data["number"] = None
        schema = LeadSchema()
        old_data = schema.dump(item, many=False)
        if "last_update" not in data:
            data["last_update"] = datetime.datetime.now()
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
        if item.customer is not None:
            item.customer.lead_number = item.number
            item.customer.reseller_id = item.reseller_id
        db.session.commit()
        add_trigger({
            "name": "lead_updated",
            "data": {
                "lead_id": item.id,
                "old_data": old_data,
                "new_data": schema.dump(item, many=False)
            }
        })
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


def get_one_item(id, fields=None):
    return get_one_item_by_model(Lead, LeadSchema, id, fields)


def send_welcome_email(lead):
    from .lead_comment_services import add_item as add_comment_item
    from app.modules.importer.sources.nocrm_io._association import find_association as nocrm_link

    if lead.id < 12664:
        return False

    if lead is None or lead.customer is None:
        raise ApiException("item_doesnt_exist", "Item doesn't exist.", 409)

    if lead.reseller_id is None or lead.reseller_id == 0:
        return False

    if lead.status != "new":
        return False

    link = nocrm_link("Lead", local_id=lead.id)
    if link is None:
        return False

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


def lead_reseller_auto_assignment(lead: Lead):
    from app.utils.google_geocoding import geocode_address

    if lead.reseller_id is not None and lead.reseller_id > 0:
        return lead
    location = geocode_address(f"${lead.customer.default_address.street} ${lead.customer.default_address.zip}  ${lead.customer.default_address.city}")
    if location is not None:
        reseller_in_range = []
        resellers = db.session.query(Reseller).all()
        min_distance = None
        min_distance_reseller = None
        for reseller in resellers:
            if reseller.sales_lat is not None and reseller.sales_lng is not None:
                distance = calculate_distance(
                    {
                        "lat": reseller.sales_lat,
                        "lng": reseller.sales_lng
                    },
                    location
                )
                if distance <= reseller.sales_range and reseller.lead_balance is not None and reseller.lead_balance < 0:
                    reseller_in_range.append(reseller)
                if min_distance is None or distance < min_distance:
                    min_distance = distance
                    min_distance_reseller = reseller
        if len(reseller_in_range) == 0 and min_distance_reseller is not None:
            update_item(lead.id, {"reseller_id": min_distance_reseller.id})
        if len(reseller_in_range) == 1:
            update_item(lead.id, {"reseller_id": reseller_in_range[0].id})
        if len(reseller_in_range) > 1:
            least_balance_reseller = reseller_in_range[0]
            for reseller in reseller_in_range:
                if least_balance_reseller.lead_balance < reseller.lead_balance:
                    least_balance_reseller = reseller
            update_item(lead.id, {"reseller_id": least_balance_reseller.id})
        db.session.add(lead)
        db.session.commit()
    return lead


def calculate_distance(location1, location2):
    from math import sin, cos, sqrt, atan2, radians

    # approximate radius of earth in km
    R = 6373.0

    lat1 = radians(location1["lat"])
    lon1 = radians(location1["lng"])
    lat2 = radians(location2["lat"])
    lon2 = radians(location2["lng"])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c

    return distance
