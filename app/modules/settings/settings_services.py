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
    data = item_schema.dump(item, many=False)
    if fields[0] != "_default_":
        data_filtered = {}
        for field in fields:
            field = field.strip()
            if field in data:
                data_filtered[field] = data[field]
        data = data_filtered
    return data


def get_settings(section=None):
    if section == "external/bitrix24":
        return {
            "select_lists": {
                "category": {
                    "15": "Cloud Verträge"
                },
                "status": {
                    "C15:NEW": "new"
                },
                "contact_source": {
                    "1": "DAA",
                    "2": "WattFox",
                    "3": "Senec",
                    "11": "T-Leads",
                    "4": "Hausfrage",
                    "16": "aroundhome",
                    "17": "BSH",
                    "OTHER": "other",
                },
            },
            "deal": {
                "fields": {
                    "street": "UF_CRM_5DD4F51D40C8D",
                    "street_nb": "UF_CRM_5DD4F51D4CA3E",
                    "city": "UF_CRM_5DD4F51D57898",
                    "zip": "UF_CRM_5DD4F51D603E2",
                    "counter_number": "UF_CRM_1585821761",
                    "power_usage": "UF_CRM_1585822072",
                    "cloud_files": "UF_CRM_1572966728920"
                }
            }
        }
    return get_one_item(section)
