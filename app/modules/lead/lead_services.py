import datetime
import random
import json

from app import db
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict
from app.modules.settings.settings_services import get_one_item as get_settings
from app.modules.settings import get_settings as get_settings2, set_settings
from app.modules.reseller.services.reseller_services import update_item as update_reseller
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
    if "last_update" not in data:
        data["last_update"] = datetime.datetime.now()
    if data["last_update"] == "no-update":
        del data["last_update"]
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
        if data["last_update"] == "no-update":
            del data["last_update"]
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


def load_commission_data(lead: Lead):
    from app.modules.importer.sources.bitrix24.order import run_import_by_lead
    lead = run_import_by_lead(lead)
    lead = lead_commission_calulation(lead)
    return lead


def lead_commission_calulation(lead: Lead):
    if lead is None or lead.reseller is None:
        return None
    is_external = lead.reseller.min_commission is not None and lead.reseller.min_commission > 0
    if lead.commissions is not None:
        for commission in lead.commissions:
            if commission["type"] == "PV":
                commission["provision_rate"] = 0
                if commission["discount_range"] == "0%":
                    commission["provision_rate"] = 10 if is_external else 6
                if commission["discount_range"] == "bis 5%":
                    commission["provision_rate"] = 8.5 if is_external else 5
                if commission["discount_range"] == "bis 8%":
                    commission["provision_rate"] = 7.5 if is_external else 4.25
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
    return lead


def auto_assignment_facebook_leads():
    from app.modules.user import auto_assign_lead_to_user
    from app.modules.external.bitrix24.lead import get_leads_by_createdate
    from app.modules.importer.sources.bitrix24.lead import run_import as run_bitrix_lead_import

    print("auto_assignment_facebook_leads")
    config = get_settings2("leads/facebook")
    print("import leads bitrix facebook")
    if config is None:
        print("no config for bitrix facebook import")
        return None
    import_time = datetime.datetime.now()
    if "last_lead_import_time" not in config:
        leads = get_leads_by_createdate('2021-01-22 00:00:00')
    else:
        leads = get_leads_by_createdate(config["last_lead_import_time"])
    if leads is None:
        print("leads could not be loaded")
        return
    for lead_data in leads:
        if lead_data["SOURCE_ID"] == "21":
            print(lead_data["ID"])
            auto_assign_lead_to_user(lead_data["ID"])
    config = get_settings2("leads/facebook")
    if config is not None:
        config["last_lead_import_time"] = import_time.astimezone().isoformat()
    set_settings("leads/facebook", config)


def lead_reseller_auto_assignment(lead: Lead):
    if lead.reseller_id is not None and lead.reseller_id > 0 and lead.reseller_id != 76:
        return lead

    reseller = find_reseller(lead)
    if reseller is not None:
        lead_reseller_assignment(lead, reseller)
        db.session.add(lead)
        db.session.commit()
    return lead


def lead_reseller_assignment(lead: Lead, reseller: Reseller):
    update_item(lead.id, {"reseller_id": reseller.id})
    balance = reseller.lead_balance if reseller.lead_balance is not None else 0
    update_reseller(
        reseller.id,
        {
            "lead_balance": balance + 1,
            "last_assigned_lead": datetime.datetime.now()
        }
    )


def find_reseller(lead):
    # from app.utils.google_geocoding import geocode_address

    # location = geocode_address(f"{lead.customer.default_address.street}, {lead.customer.default_address.zip}  {lead.customer.default_address.city}")
    # if location is None:
    #    return None

    print("reseller auto assign:", lead.id)
    reseller_in_range = []
    resellers = db.session.query(Reseller).filter(Reseller.lead_balance < 0).filter(Reseller.active.is_(True)).all()

    min_distance = None
    min_distance_reseller = None
    for reseller in resellers:
        if reseller.ziplist is not None:
            if lead.customer.default_address.zip in reseller.ziplist:
                print("reseller ziplist", reseller.id)
                reseller_in_range.append(reseller)

    if len(reseller_in_range) == 0:
        kammandel = db.session.query(Reseller).get(76)
        print("kammandel", kammandel.id)
        return kammandel

    if len(reseller_in_range) == 1:
        print("only one found", reseller_in_range[0].id)
        return reseller_in_range[0]

    if len(reseller_in_range) > 1:
        least_balance_reseller = reseller_in_range[0]
        if least_balance_reseller.last_assigned_lead is not None:
            for reseller in reseller_in_range:
                if reseller.last_assigned_lead is None:
                    least_balance_reseller = reseller
                    break
                if reseller.last_assigned_lead < least_balance_reseller.last_assigned_lead:
                    least_balance_reseller = reseller
        print("multiple found", least_balance_reseller.id)
        return least_balance_reseller


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
