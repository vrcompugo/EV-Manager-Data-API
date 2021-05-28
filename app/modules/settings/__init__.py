import datetime
import os
import sys

from app import db
from flask import request
from app.utils.set_attr_by_dict import set_attr_by_dict
from app.modules.auth import get_auth_info, get_logged_in_user
from app.exceptions import ApiException
from .models.settings import Settings


def get_full_section_name(section, domain_raw=None):

    domain_raw = "keso.bitrix24.de"
    return f"{domain_raw}/{section}"


def get_settings(section=None, domain_raw=None):
    full_section = get_full_section_name(section, domain_raw)
    settings_object = db.session.query(Settings).filter(Settings.section == full_section).first()
    if settings_object is not None:
        return settings_object.data
    if full_section == "keso.bitrix24.de/general":
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
    if full_section == "keso.bitrix24.de/offer/datasheet_pdf":
        data = {
            "financing_file_id": 769,
            "senec_340wp": 435,
            "glas_glas": 445,
            "senec_v3": 437,
            "senec_guarantee": 441,
            "symo": 433
        }
        return data
    if full_section == "keso.bitrix24.de/offer/summary_pdf":
        data = {
            "backside_file_id": 493
        }
        return data
    if full_section == "keso.bitrix24.de/external/bitrix24":
        data = {
            "url": "https://keso.bitrix24.de/rest/106/v38b9iovomrydti2/",
            "taxrate": 19,
            "select_lists": {
                "heating_type": {
                },
                "salutation": {
                    "HNR_DE_2": "mr",
                    "HNR_DE_1": "ms"
                },
                "mfr_category": {
                    "": "default",
                    "3978": "electric",
                    "3980": "roof",
                    "3982": "heating",
                    "3984": "service",
                    "4044": "holiday",
                    "4042": "roof_reconstruction_pv",
                    "4040": "roof_reconstruction",
                    "4038": "service_storage_pb",
                    "4034": "service_storage_li",
                    "4030": "service_pv_storage_li",
                    "4018": "service_pv_storage_pb",
                    "4016": "storage_swap",
                    "4014": "repair_electric",
                    "4012": "additional_roof",
                    "4010": "solar_edge_change_test",
                    "4054": "enpal_mvt",
                    "4056": "enpal_verbau",
                    "4074": "additional_electric"
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
                    "Heizung - Optionen für Heizung Gas/Öl": 220,
                    "Heizung - Optionen für Heizung online": 302,
                    "Heizung - Solarthermie": 240,
                    "Erneuerbare Energie - Dach": 194,
                    "Brennstoffzelle": 298,
                    "online WP (Neu)": 306,
                    "Texte": 304,
                    "Dachsanierung online Bogen": 290,
                    "Optionen Heizung online": 302,
                    "Solarthermie online": 300
                }
            },
            "task": {
                "fields": {
                    "mfr_id": "ufAuto422491195439",
                    "etermin_id": "ufAuto219922666303",
                    "mfr_appointments": "ufAuto343721853755",
                    "etermin_appointments": "ufAuto513701476131"
                },
                "leading_users": {
                    "onur.berber.e360@gmail.com": "410",
                    "bernd.buechsenschuetz.kez@gmail.com": "70",
                    "dieter.hartmann.kez@gmail.com": "72",
                    "heiko.burzlaff.kez@gmail.com": "76",
                    "jason.hardy.kez@gmail.com": "100",
                    "joudi.daher.kez@gmail.com": "68",
                    "liviu.vasile.kez@gmail.com": "74",
                    "marco.gentsch.kez@gmail.com": "56",
                    "kbez330@gmail.com": "90",
                    "maurice.dobes.kez@gmail.com": "96",
                    "becker@korbacher-energiezentrum.de": "320",
                    "nebras.aboumoghdeb.kez@gmail.com": "58",
                    "rafat.alkuferi.kez@gmail.com": "62",
                    "rene.schroeder.kez@gmail.com": "298",
                    "roesner@energie360.de": "408",
                    "ronny.pokutta.kez@gmail.com": "64",
                    "volker.boemeke.kez@gmail.com": "98",
                    "mario.scherbaum.e360@gmail.com": "412"
                }
            },
            "deal": {
                "fields": {
                    "mfr_service_object_id": "UF_CRM_1612190018299",
                    "unique_identifier": "UF_CRM_5FA43F983EBAB",
                    "drive_insurance_folder": "UF_CRM_1612521127848",
                    "drive_rental_contract_folder": "UF_CRM_1612534834920",
                    "drive_rental_documents_folder": "UF_CRM_1612534862483",
                    "drive_cloud_folder": "UF_CRM_1612535045945",
                    "mfr_category": "UF_CRM_1612967946042",
                    "service_appointment_notes": "UF_CRM_1573029988665",
                    "service_appointment_date": "UF_CRM_1594740636",
                    "service_appointment_startdate": "UF_CRM_1614935800",
                    "service_appointment_enddate": "UF_CRM_1614935821",
                    "etermin_id": "UF_CRM_1614177772351",
                    "upload_link_roof": "UF_CRM_1600762711357",
                    "upload_link_electric": "UF_CRM_1600762741782",
                    "upload_link_heating": "UF_CRM_1600762727113",
                    "upload_link_invoices": "UF_CRM_1600762755535",
                    "upload_link_contract": "UF_CRM_1600762796533",
                    "upload_link_firstcall": "UF_CRM_1618302925",
                    "upload_link_heatingcontract": "UF_CRM_60A60FF556B0C",
                    "folder_id_heatingcontract": "UF_CRM_1621504031",
                    "aev_reseller": "UF_CRM_1615824273",
                    "contract_number": "UF_CRM_1596704551167",
                    "fakturia_contract_number": "UF_CRM_1622107557802",
                    "cloud_delivery_begin": "UF_CRM_1578322109"
                }
            },
            "quote": {
                "units": {
                    "None": "Stück",
                    "6": "Meter",
                    "112": "Liter",
                    "163": "Gramm",
                    "166": "Kilogramm",
                    "796": "Stück",
                    "101": "Monate á",
                    "123": "kWp",
                    "124": "kWh",
                    "125": "AW",
                    "126": "m²",
                    "127": "m³"
                },
                "fields": {
                    "unique_identifier": "UF_CRM_1607078985",
                    "history_id": "UF_CRM_1607079008",
                    "pdf_link": "UF_CRM_1607079246",
                    "quote_number": "UF_CRM_1607085112",
                    "special_conditions": "TERMS",
                    "expected_construction_week": "UF_CRM_1607444032"
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
                    "upload_link_firstcall": "UF_CRM_1618302626914",
                    "upload_link_heatingcontract": "UF_CRM_1621495505",
                    "salutation": "HONORIFIC",
                    "first_name": "NAME",
                    "street": "UF_CRM_5DD4020221169",
                    "street_nb": "UF_CRM_5DD402022E300",
                    "zip": "UF_CRM_5DD4020242167",
                    "city": "UF_CRM_5DD4020239456",
                    "aev_reseller": "UF_CRM_1615824261",
                    "collection_url": "UF_CRM_1620134803"
                }
            },
            "company": {
                "fields": {
                    "street": "UF_CRM_5DE18F4023B26",
                    "street_nb": "UF_CRM_5DE18F402C2CC",
                    "zip": "UF_CRM_5DE18F403BE8A",
                    "city": "UF_CRM_5DE18F4033826",
                    "mfr_id": "UF_CRM_1611663098516",
                    "mfr_service_object_id": "UF_CRM_1612189949145"
                }
            },
            "contact": {
                "fields": {
                    "salutation": "HONORIFIC",
                    "first_name": "NAME",
                    "street": "UF_CRM_1572950758",
                    "street_nb": "UF_CRM_1572950777",
                    "zip": "UF_CRM_1572963458",
                    "city": "UF_CRM_1572963448",
                    "fakturia_number": "UF_CRM_1611055654633",
                    "mfr_id": "UF_CRM_1611663069960",
                    "mfr_service_object_id": "UF_CRM_1612189860475",
                    "drive_myportal_folder": "UF_CRM_1612518385676",
                    "drive_abnahmen_folder": "UF_CRM_1612533349639",
                    "drive_internal_folder": "UF_CRM_1612533369175",
                    "drive_service_protocol_folder": "UF_CRM_1612533388171",
                    "drive_order_confirmation_folder": "UF_CRM_1612533409927",
                    "drive_orgamax_folder": "UF_CRM_1612533423669",
                    "drive_insurance_folder": "UF_CRM_1612533445604",
                    "drive_remote_care_folder": "UF_CRM_1612533596622",
                    "drive_rental_contract_folder": "UF_CRM_1612533461553",
                    "drive_rental_documents_folder": "UF_CRM_1612533480143",
                    "drive_cloud_folder": "UF_CRM_1612533500465"
                }
            },
            "timeline_comment": {
                "fields": {
                }
            }
        }
        return data
    return {}


def set_settings(section, data, domain_raw=None):
    full_section = get_full_section_name(section, domain_raw)
    settings_object = db.session.query(Settings).filter(Settings.section == full_section).first()
    if settings_object is None:
        raise ApiException("settings not found", "Einstellungen wurden nicht gefunden", 500)
    settings_object.data = data
    db.session.commit()
    return settings_object.data


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
