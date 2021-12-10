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


def get_one_item(section, fields=None, options=None):
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
                "emove_tarif": {
                    "2436": "",
                    "2428": "emove Tarif Hybrid",
                    "2430": "emove.drive I",
                    "2432": "emove.drive II",
                    "2434": "emove.drive II",
                    "2446": "emove.drive ALL",
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
                    "offer_number": "UF_CRM_1596703818172",
                    "power_meter_number": "UF_CRM_1585821761",
                    "usage": "UF_CRM_1585822072",
                    "power_usage": "UF_CRM_1597757913754",
                    "heater_usage": "UF_CRM_1597757931782",
                    "heatcloud_power_meter_number": "UF_CRM_1597757955687",
                    "price_guarantee": "UF_CRM_1597758014166",
                    "emove_tarif": "UF_CRM_1594062176",
                    "cloud_configuration_file": "UF_CRM_1596704122354",
                    "cloud_configuration_file_link": "UF_CRM_1598964158",
                    "cloud_files": "UF_CRM_1572966728920",
                    "contract_number": "UF_CRM_1596704551167",
                    "has_consumer": "UF_CRM_1597755071841",
                    "is_consumer": "UF_CRM_1597755099494",
                    "has_ecloud": "UF_CRM_1597755087885",
                    "construction_date": "UF_CRM_1585237939",
                    "smartme_number": "UF_CRM_1605610632"
                }
            }
        }
    return get_one_item(section)
