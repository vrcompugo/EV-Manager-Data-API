import datetime
import os

from app import db
from flask import request
from app.utils.set_attr_by_dict import set_attr_by_dict
from app.modules.auth import get_auth_info

from .models.settings import Settings


def get_settings(section=None, domain_raw=None):
    if domain_raw is None:
        domain_raw = ""
        auth_info = get_auth_info()
        if "domain_raw" in auth_info:
            domain_raw = auth_info["domain_raw"]
        if request is not None:
            if request.args.get("DOMAIN") is not None:
                domain_raw = request.args.get('DOMAIN')
            if request.form.get("auth[domain]") is not None:
                domain_raw = request.form.get('auth[domain]')
            if hasattr(request, "bitrix_domain") and request.bitrix_domain is not None:
                domain_raw = request.bitrix_domain
    if f"{domain_raw}/{section}" == "keso.bitrix24.de/general":
        if os.getenv('ENVIRONMENT') == "dev":
            return {
                "base_url": "https://api.korbacher-energiezentrum.de.ah.hbbx.de/"
            }
        if os.getenv('ENVIRONMENT') == "staging":
            return {
                "base_url": "https://staging.api.korbacher-energiezentrum.de.ah.hbbx.de/"
            }
        return {
            "base_url": "https://api.korbacher-energiezentrum.de/"
        }
    if f"{domain_raw}/{section}" == "keso.bitrix24.de/offer/datasheet_pdf":
        data = {
            "financing_file_id": 769,
            "senec_340wp": 435,
            "glas_glas": 445,
            "senec_v3": 437,
            "senec_guarantee": 441,
            "symo": 433
        }
        return data
    if f"{domain_raw}/{section}" == "keso.bitrix24.de/offer/summary_pdf":
        data = {
            "backside_file_id": 493
        }
        return data
    if f"{domain_raw}/{section}" == "keso.bitrix24.de/external/bitrix24":
        data = {
            "url": "https://keso.bitrix24.de/rest/106/yyd10rau6od3jlan/",
            "taxrate": 19,
            "select_lists": {
                "heating_type": {
                },
                "salutation": {
                    "HNR_DE_2": "mr",
                    "HNR_DE_1": "ms"
                }
            },
            "product": {
                "units": {
                    "None": "Stück",
                    "1": "Meter",
                    "3": "Liter",
                    "5": "Gramm",
                    "7": "Kilogramm",
                    "9": "Stück",
                    "10": "Monate á",
                    "12": "kWp",
                    "14": "kWh",
                    "16": "AW",
                    "18": "m²",
                    "20": "m³"
                },
                "categories": {
                    "": None,
                    "Elektrik": 266,
                    "Optionen PV Anlage": 262,
                    "Extra Pakete": 292,
                    "PV Module": 260,
                    "Stromspeicher": 264,
                    "Brauchwasserwärmepumpe": 150,
                    "Wärmepumpe": 282,
                    "Heizung - WP": 218,
                    "Heizung - Gas": 238,
                    "Heizung - Öl": 216,
                    "Heizung - Optionen für Heizung": 220,
                    "Heizung - Optionen für Heizung online": 302,
                    "Heizung - Solarthermie": 240,
                    "Erneuerbare Energie - Dach": 194,
                    "Texte": 304,
                }
            },
            "deal": {
                "fields": {
                }
            },
            "lead": {
                "fields": {
                    "unique_identifier": "UF_CRM_1603895163",
                    "pdf_datasheets_link": "UF_CRM_1603981997",
                    "pdf_summary_link": "UF_CRM_1603982021",
                    "pdf_quote_summary_link": "UF_CRM_1603982035",
                    "pdf_contract_summary_link": "UF_CRM_1603982051",
                    "upload_link_roof": "UF_CRM_1603982144",
                    "upload_link_electric": "UF_CRM_1603982169",
                    "upload_link_heating": "UF_CRM_1603982160",
                    "upload_link_invoices": "UF_CRM_1603982179",
                    "upload_link_contract": "UF_CRM_1603982205",
                    "salutation": "HONORIFIC",
                    "first_name": "NAME",
                    "street": "UF_CRM_5DD4020221169",
                    "street_nb": "UF_CRM_5DD402022E300",
                    "zip": "UF_CRM_5DD4020242167",
                    "city": "UF_CRM_5DD4020239456"
                }
            },
            "contact": {
                "fields": {
                    "salutation": "HONORIFIC",
                    "first_name": "NAME",
                    "street": "UF_CRM_1572950758",
                    "street_nb": "UF_CRM_1572950777",
                    "zip": "UF_CRM_1572963458",
                    "city": "UF_CRM_1572963448"
                }
            }
        }
        if datetime.datetime.now() >= datetime.datetime(2020, 7, 1) and datetime.datetime.now() < datetime.datetime(2021, 1, 1):
            data["taxrate"] = 16
        return data
    return {}


def set_settings(section=None):
    pass


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


def import_test_data():
    pass
