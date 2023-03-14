
import requests
import json
import os
import datetime
from flask import Blueprint, request, render_template, redirect, make_response, Response
from flask_emails import Message
from sqlalchemy import not_
from dateutil.parser import parse

from app import db
from app.config import email_config
from app.decorators import api_response, log_request
from app.modules.auth import get_auth_info, validate_jwt
from app.modules.auth.jwt_parser import decode_jwt, encode_jwt, encode_shared_jwt
from app.modules.external.bitrix24.lead import get_lead, update_lead, add_lead
from app.modules.external.bitrix24.deal import get_deal, update_deal
from app.modules.external.bitrix24.quote import get_quote, add_quote, update_quote_products
from app.modules.external.bitrix24.drive import get_file, add_file, get_folder_id, get_public_link, create_folder_path
from app.modules.external.bitrix24.products import reload_products
from app.modules.external.bitrix24.contact import add_contact
from app.modules.external.insign.models.insign_log import InsignLog
from app.modules.settings import get_settings
from app.modules.cloud.services.calculation import get_cloud_products
from app.modules.offer.offer_services import add_item_v2, update_item_v2, get_one_item_v2
from app.models import OfferV2

from .quote_data import calculate_quote, calculate_heating_usage
from .generator import generate_commission_pdf, generate_order_confirmation_pdf, generate_bluegen_pdf, generate_bluegen_wi_pdf, generate_cover_pdf, generate_quote_pdf, generate_datasheet_pdf, generate_summary_pdf, generate_letter_pdf, generate_contract_summary_pdf, generate_heating_pdf, generate_roof_reconstruction_pdf, generate_quote_summary_pdf, generate_contract_summary_part1_pdf, generate_contract_summary_part2_pdf, generate_contract_summary_part3_pdf, generate_contract_summary_part4_pdf, generate_contract_summary_part4_1_pdf, generate_contract_summary_part5_pdf, generate_heatpump_auto_generate_pdf
from .models.quote_history import QuoteHistory


blueprint = Blueprint("quote_calculator", __name__, template_folder='templates')


UNCALCULATED_FIELDS = [
    # customer data
    "birthday", "iban", "bic", "bankname", "extra_notes", "cloud_number", "solaredge_designer_link",
    # elektro tab
    "tab_building_type", "oberleitung_vorhanden", "kabelkanal_color", "tab_has_cellar_external_entrance",
    "is_new_building", "power_meter_number", "main_malo_id", "heatcloud_power_meter_number",
    "power_meter_number_extra1_label", "power_meter_number_extra1",
    "power_meter_number_extra2_label", "power_meter_number_extra2",
    "tab_zahlerzusammenlegung", "tab_extra_counter_number1", "tab_extra_counter_number2", "tab_extra_counter_number3",
    "tab_hak_position", "tab_distance_hak", "tab_roomheight_power_cabinet",
    "tab_power_usage_options", "wallbox_mountpoint", "tab_power_usage_total_power",
]
UNCALCULATED_FIELDS_CONSUMER = [
    "power_meter_number", "malo_id", "address"
]
UNCALCULATED_FIELDS_ROOF = [
    "label", "roof_type", "insulation_type", "insulation_thickness", "insulation_material"
]


@blueprint.route("/reload_products", methods=['GET', 'POST'])
@log_request
def route_reload_products():
    reload_products(force=True)
    return {"status": "success"}


@blueprint.route("/uploader/<token>", methods=['GET', 'POST'])
def route_uploader_token(token):
    data = decode_jwt(token)
    history = QuoteHistory.query.filter(QuoteHistory.lead_id == data["unique_identifier"]).order_by(QuoteHistory.datetime.desc()).first()
    if history is None:
        return {"status": "failed"}
    return {"status": "success", "data": history.data}


@blueprint.route("/history/<history_id>", methods=['PUT'])
@log_request
def edit_history(history_id):
    auth_info = get_auth_info()
    if auth_info is not None and auth_info["domain_raw"] == "keso.bitrix24.de":
        history = QuoteHistory.query.filter(QuoteHistory.id == int(history_id)).filter(QuoteHistory.is_complete.is_(True)).first()
        if history is not None:
            data = request.json
            history.label = data.get("label")
            db.session.commit()
            return {"status": "success", "data": {
                "id": history.id,
                "datetime": history.datetime,
                "label": history.label
            }}
        return {"status": "failed", "data": {}, "message": "history not found"}
    return {"status": "failed", "data": {}, "message": "auth failed"}


@blueprint.route("/history/<history_id>/push", methods=['POST'])
@log_request
def push_history(history_id):
    auth_info = get_auth_info()
    if auth_info is not None and auth_info["domain_raw"] == "keso.bitrix24.de":
        history = QuoteHistory.query.filter(QuoteHistory.id == int(history_id)).first()
        lead = get_lead(history.lead_id, True)
        if lead.get("collection_url") not in [None, "", 0, "0"]:
            return Response(
                '{"status": "error", "error_code": "already_signed", "message": "Der Lead wurde bereits unterschrieben. Angebotserstellung nicht mehr möglich"}',
                status=200,
                mimetype='application/json')
        if history is not None:
            history.datetime = datetime.datetime.now()
            db.session.commit()
            return {"status": "success", "data": {
                "id": history.id,
                "datetime": history.datetime,
                "label": history.label
            }}
        return {"status": "failed", "data": {}, "message": "history not found"}
    return {"status": "failed", "data": {}, "message": "auth failed"}


@blueprint.route("/<lead_id>", methods=['GET', 'POST'])
@log_request
def quote_calculator_defaults(lead_id):
    auth_info = get_auth_info()
    if auth_info is not None and auth_info["domain_raw"] == "keso.bitrix24.de":
        data = quote_calculator_set_defaults(lead_id)
        return Response(
            json.dumps({"status": "success", "data": data}),
            status=200,
            mimetype='application/json')
    return Response(
        '{"status": "error", "error_code": "not_authorized", "message": "user not authorized for this action"}',
        status=501,
        mimetype='application/json')


def quote_calculator_set_defaults(lead_id):
    lead_id = int(lead_id)
    if lead_id <= 0:
        return Response(
            '{"status": "error", "error_code": "not_deal_given", "message": "deal id missing in data object"}',
            status=404,
            mimetype='application/json')

    history = QuoteHistory.query.filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    if history is not None and history.is_complete is not True:
        history_quote = QuoteHistory.query.filter(QuoteHistory.lead_id == lead_id).filter(QuoteHistory.is_complete).order_by(QuoteHistory.datetime.desc()).first()
        if history_quote is not None:
            if history.data is not None:
                history.data["pdf_link"] = history_quote.data.get("pdf_link")
                history.data["pdf_wi_link"] = history_quote.data.get("pdf_wi_link")
                history.data["cloud_number"] = history_quote.data.get("cloud_number")
                history.data["pdf_summary_link"] = history_quote.data.get("pdf_summary_link")
                history.data["pdf_commission_link"] = history_quote.data.get("pdf_commission_link")
                history.data["pdf_datasheets_link"] = history_quote.data.get("pdf_datasheets_link")
                history.data["pdf_quote_summary_link"] = history_quote.data.get("pdf_quote_summary_link")
                history.data["pdf_contract_summary_link"] = history_quote.data.get("pdf_contract_summary_link")
                history.data["pdf_contract_summary_part1_file_id"] = history_quote.data.get("pdf_contract_summary_part1_file_id")
                history.data["pdf_contract_summary_part4_file_link"] = history_quote.data.get("pdf_contract_summary_part4_file_link")
                history.data["pdf_contract_summary_part4_1_file_link"] = history_quote.data.get("pdf_contract_summary_part4_1_file_link")
            else:
                history.data = history_quote.data
    if history is not None and history.data is not None:
        data = history.data
        data["history_id"] = history.id
        if "roofs" not in data["data"]:
            roof = {
                "direction": "west_east",
                "is_valid": True,
                "is_valid_body": True,
                "is_valid_header": True,
                "label": "Rekonstruiert",
                "pv_count_modules": 1,
                "pv_kwp_used": 1
            }
            if "roof_direction" in data["data"]:
                roof["direction"] = data["data"]["roof_direction"]
            if "pv_kwp" in data["data"]:
                roof["pv_kwp_used"] = data["data"]["pv_kwp"]
            data["data"]["roofs"] = [roof]
        if "financing_rate" not in data["data"]:
            data["data"]["financing_rate"] = 3.79
        if "financing_rate_heating" not in data["data"]:
            data["data"]["financing_rate_heating"] = 3.79
        if "extra_options_zero" not in data["data"]:
            data["data"]["extra_options_zero"] = []
        if "extra_options" not in data["data"]:
            data["data"]["extra_options"] = []
        if "tab_power_usage_options" not in data["data"]:
            data["data"]["tab_power_usage_options"] = []
        if "solaredge" not in data["data"]["extra_options"]:
            data["data"]["extra_options"].append("solaredge")
        data["quote_datetime"] = data["datetime"]
        if "status_id" not in data["data"]:
            lead_data = get_lead(lead_id)
            data["data"]["status_id"] = lead_data.get("status_id")
        data2 = calculate_quote(lead_id)
        data["select_options"] = data2["select_options"]
    else:
        post_data = None
        try:
            post_data = request.json
        except Exception as e:
            pass
        data = calculate_quote(lead_id, post_data)
        data["quote_datetime"] = str(datetime.datetime.now())

    lead = get_lead(lead_id)
    update_data = {}
    if "unique_identifier" not in lead or lead["unique_identifier"] is None or lead["unique_identifier"] == "":
        lead["unique_identifier"] = lead_id
        update_data["unique_identifier"] = str(lead_id)
    folders = [
        { "key": "roof", "path": "/Uploads/Dachbilder" },
        { "key": "roof_extra", "path": "/Uploads/Weitere Dachbilder" },
        { "key": "tab", "path": "/Uploads/TAB" },
        { "key": "electric", "path": "/Uploads/Elektrik-Bilder" },
        { "key": "heating", "path": "/Uploads/Heizungsbilder" },
        { "key": "invoices", "path": "/Uploads/Rechnung vom bisherigem Anbieter" },
        { "key": "contract", "path": "/Uploads/Vertragsunterlagen" },
        { "key": "firstcall", "path": "/Uploads/First Call" },
    ]
    for folder in folders:
        if f"upload_link_{folder['key']}" not in data["data"] or data["data"][f"upload_link_{folder['key']}"].find(f"Vorgang {lead['unique_identifier']}") < 0:
            data["data"][f"upload_folder_id_{folder['key']}"] = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}{folder['path']}")
            data["data"][f"upload_link_{folder['key']}"] = f"https://keso.bitrix24.de/docs/path/Auftragsordner/Vorgang {lead['unique_identifier']}{folder['path']}"
            update_data[f"upload_folder_id_{folder['key']}"] = data["data"][f"upload_folder_id_{folder['key']}"]
            update_data[f"upload_link_{folder['key']}"] = data["data"][f"upload_link_{folder['key']}"]
    if lead.get("eos_upload_files") in [None, "", 0, "0"]:
        token_data = {
            "unique_identifier": lead["unique_identifier"]
        }
        update_data["eos_upload_files"] = f"https://api.korbacher-energiezentrum.de/vue/quote_calculator/uploader/{encode_jwt(token_data, expire_minutes=60*24*180)['token']}"
    if len(update_data.keys()) > 0:
        update_lead(lead_id, update_data)
    histories = QuoteHistory.query.filter(QuoteHistory.lead_id == lead_id).filter(QuoteHistory.is_complete.is_(True)).order_by(QuoteHistory.datetime.desc()).all()
    data["histories"] = []
    for history in histories:
        data["histories"].append({
            "id": history.id,
            "datetime": str(history.datetime),
            "label": history.label
        })
    return data


@blueprint.route("/<lead_id>/calculate", methods=['GET', 'POST'])
@api_response
@log_request
def quote_calculator_calculate(lead_id):
    auth_info = get_auth_info()
    if auth_info is not None and auth_info["domain_raw"] == "keso.bitrix24.de":
        post_data = None
        try:
            post_data = request.json
        except Exception as e:
            pass
        lead_id = int(lead_id)
        if lead_id <= 0:
            return Response(
                '{"status": "error", "error_code": "not_deal_given", "message": "deal id missing in data object"}',
                status=404,
                mimetype='application/json')
        form_dirty = False
        form_updated = False
        history_quote = QuoteHistory.query.filter(QuoteHistory.lead_id == lead_id).filter(QuoteHistory.is_complete).order_by(QuoteHistory.datetime.desc()).first()
        if history_quote is not None:
            history_data = json.loads(json.dumps(history_quote.data))
            for key in post_data.keys():
                if key == "solaredge_designer_link":
                    if str(history_data["data"].get(key)) != str(post_data.get(key)):
                        form_updated = True
                        print("update detected", key)
                        update_lead(lead_id, {
                            "solaredge_designer_link": post_data.get(key)
                        })
                        history_data["data"][key] = post_data.get(key)
                elif is_uncalculated_field(key):
                    if str(history_data["data"].get(key)) != str(post_data.get(key)):
                        if not is_temp_field(key):
                            form_updated = True
                            print("update detected", key)
                        history_data["data"][key] = post_data.get(key)
                else:
                    if key in ["consumers", "roofs"]:
                        if post_data.get(key) is None or history_quote.data["data"].get(key) is None or len(post_data[key]) != len(history_quote.data["data"][key]):
                            form_dirty = True
                        else:
                            for index in range(len(post_data[key])):
                                for key2 in post_data[key][index].keys():
                                    if key2 not in UNCALCULATED_FIELDS_CONSUMER and key2 not in UNCALCULATED_FIELDS_ROOF:
                                        if is_uncalculated_field(key2):
                                            if not is_temp_field(key2):
                                                form_updated = True
                                                print("update detected", key, index, key2)
                                        else:
                                            if is_value_changed(post_data[key][index][key2], history_quote.data["data"][key][index].get(key2)):
                                                print("dirty detected", key, index, key2)
                                                form_dirty = True
                    else:
                        if is_value_changed(post_data[key], history_quote.data["data"].get(key)):
                            print("dirty detected", key)
                            form_dirty = True
            history_quote.data = history_data
            db.session.commit()
            history_dirty = QuoteHistory.query\
                .filter(QuoteHistory.lead_id == lead_id)\
                .filter(not_(QuoteHistory.is_complete))\
                .filter(QuoteHistory.datetime >= history_quote.datetime)\
                .order_by(QuoteHistory.datetime.desc()).first()
        else:
            history_dirty = QuoteHistory.query.filter(QuoteHistory.lead_id == lead_id).filter(not_(QuoteHistory.is_complete)).order_by(QuoteHistory.datetime.desc()).first()

        if history_dirty is None:
            if form_dirty is False and history_quote is not None:
                if form_updated or \
                    history_quote.data.get("pdf_contract_summary_link_datetime") is None or \
                    parse(history_quote.data.get("pdf_contract_summary_link_datetime")) < datetime.datetime.now() - datetime.timedelta(days=1):
                    history_data = json.loads(json.dumps(history_quote.data))
                    history_data["pdf_contract_summary_link"] = None
                    history_data["pdf_contract_summary_part1_file_id"] = None
                    history_data["pdf_contract_summary_part4_1_file_link"] = None
                    history_quote.data = history_data
                    db.session.commit()
                return Response(
                    json.dumps({"status": "success", "data": history_quote.data}),
                    status=200,
                    mimetype='application/json')
            history_dirty = QuoteHistory(
                lead_id=lead_id,
                datetime=datetime.datetime.now(),
                label="",
                data=None,
                is_complete=False
            )
            db.session.add(history_dirty)
            db.session.flush()
        data = calculate_quote(lead_id, post_data)
        if history_quote is not None:
            data["pdf_commission_link"] = history_quote.data.get("pdf_commission_link")
        data["history_id"] = history_dirty.id
        history_dirty.data=data
        db.session.commit()


        return Response(
            json.dumps({"status": "success", "data": data}),
            status=200,
            mimetype='application/json')
    return Response(
        '{"status": "error", "error_code": "not_authorized", "message": "user not authorized for this action"}',
        status=501,
        mimetype='application/json')


@blueprint.route("/<lead_id>/uploader_store", methods=['POST'])
@api_response
def quote_calculator_uploader_store(lead_id):
    auth_info = None
    try:
        raw = validate_jwt()
        if raw.get("unique_identifier") == lead_id:
            auth_info = raw
    except Exception as e:
        pass
    if auth_info is None:
        auth_info = get_auth_info()
    if auth_info is None:
        return Response(
            '{"status": "error", "error_code": "not_authorized", "message": "user not authorized for this action"}',
            status=501,
            mimetype='application/json')
    post_data = request.json
    lead_id = int(lead_id)
    history_quote = QuoteHistory.query.filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    history_quote_complete = QuoteHistory.query.filter(QuoteHistory.lead_id == lead_id).filter(QuoteHistory.is_complete).order_by(QuoteHistory.datetime.desc()).first()
    data2 = None
    data = json.loads(json.dumps(history_quote.data))
    if history_quote_complete is not None:
        data2 = json.loads(json.dumps(history_quote_complete.data))
    for key in post_data.keys():
        if isinstance(post_data[key], list):
            pass
        if isinstance(post_data[key], list):
            pass
        if key[:8] == "tab_img_" or key[:12] == "tab_comment_":
            data["data"][key] = post_data[key]
            if data2 is not None:
                data2["data"][key] = post_data[key]
    history_quote.data = data
    if history_quote_complete is not None:
        history_quote_complete.data = data2
    db.session.commit()
    return Response(
        json.dumps({"status": "success", "data": history_quote.data}),
        status=200,
        mimetype='application/json')


@blueprint.route("/<lead_id>/upload_file", methods=['POST'])
@api_response
def quote_calculator_upload_file(lead_id):
    auth_info = None
    try:
        raw = validate_jwt()
        if raw.get("unique_identifier") == lead_id:
            auth_info = raw
    except Exception as e:
        pass
    if auth_info is None:
        auth_info = get_auth_info()
    if auth_info is not None:
        post_data = request.form
        lead_id = int(lead_id)
        if lead_id <= 0:
            return Response(
                '{"status": "error", "error_code": "not_deal_given", "message": "deal id missing in data object"}',
                status=404,
                mimetype='application/json')
        lead = get_lead(lead_id)
        subfolder_id = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Uploads/{os.path.dirname(post_data.get('path'))}")
        file_id = add_file(subfolder_id, data={
            "file": request.files.get("file"),
            "filename": os.path.basename(post_data.get('path'))
        })
        print(file_id)

        return Response(
            json.dumps({"status": "success", "data": { "file_id": file_id } }),
            status=200,
            mimetype='application/json')
    return Response(
        '{"status": "error", "error_code": "not_authorized", "message": "user not authorized for this action"}',
        status=501,
        mimetype='application/json')


@blueprint.route("/<lead_id>/view_upload_file", methods=['POST'])
@api_response
def quote_calculator_view_upload_file(lead_id):
    auth_info = None
    try:
        raw = validate_jwt()
        if raw.get("unique_identifier") == lead_id:
            auth_info = raw
    except Exception as e:
        pass
    if auth_info is None:
        auth_info = get_auth_info()
    if auth_info is not None:
        post_data = request.json
        lead_id = int(lead_id)
        if lead_id <= 0:
            return Response(
                '{"status": "error", "error_code": "not_deal_given", "message": "deal id missing in data object"}',
                status=404,
                mimetype='application/json')
        if 'file_id' in post_data:
            public_link = get_public_link(post_data['file_id'], extra_data={"resize": "200x200"})
            is_sample = False
        else:
            public_link = '/static/tab/samples/' + post_data['samplepath']
            is_sample = True
        return Response(
            json.dumps({"status": "success", "data": {'public_url': public_link, "is_sample": is_sample}}),
            status=200,
            mimetype='application/json')
    return Response(
        '{"status": "error", "error_code": "not_authorized", "message": "user not authorized for this action"}',
        status=501,
        mimetype='application/json')


@blueprint.route("/<lead_id>/calculate_heating_usage", methods=['POST'])
@api_response
@log_request
def quote_calculator_calculate_heating_usage(lead_id):
    auth_info = get_auth_info()
    if auth_info is not None and auth_info["domain_raw"] == "keso.bitrix24.de":
        post_data = None
        try:
            post_data = request.json
        except Exception as e:
            pass
        lead_id = int(lead_id)
        if lead_id <= 0:
            return Response(
                '{"status": "error", "error_code": "not_deal_given", "message": "deal id missing in data object"}',
                status=404,
                mimetype='application/json')
        data = calculate_heating_usage(lead_id, post_data)
        return Response(
            json.dumps({"status": "success", "data": data}),
            status=200,
            mimetype='application/json')
    return Response(
        '{"status": "error", "error_code": "not_authorized", "message": "user not authorized for this action"}',
        status=501,
        mimetype='application/json')


@blueprint.route("/<lead_id>", methods=['PUT'])
@log_request
def quote_calculator_update(lead_id):
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return Response(
            '{"status": "error", "error_code": "not_authorized", "message": "user not authorized for this action"}',
            status=501,
            mimetype='application/json')
    print(auth_info)
    post_data = None
    try:
        post_data = request.json
    except Exception as e:
        pass
    lead_id = int(lead_id)
    if lead_id <= 0:
        return Response(
            '{"status": "error", "error_code": "not_deal_given", "message": "deal id missing in data object"}',
            status=404,
            mimetype='application/json')

    return quote_calculator_add_history(lead_id, post_data, auth_info)


def quote_calculator_add_history(lead_id, post_data, auth_info=None):
    if auth_info is not None:
        auth_info["user"].get("uf_department")
    contact_id = None
    lead = get_lead(lead_id, True)
    if lead.get("collection_url") not in [None, "", 0, "0"]:
        if auth_info is None or (7 not in auth_info["user"].get("uf_department") and 41 not in auth_info["user"].get("uf_department")):
            return Response(
                '{"status": "error", "error_code": "already_signed", "message": "Der Lead wurde bereits unterschrieben. Angebotserstellung nicht mehr möglich"}',
                status=200,
                mimetype='application/json')

    if lead["contact_id"] is None or lead["contact_id"] is False or lead["contact_id"] == "" or int(lead["contact_id"]) == 0:
        contact = add_contact(lead["contact"])
        contact_id = contact.get("id", None)
    if "unique_identifier" not in lead or lead["unique_identifier"] is None or lead["unique_identifier"] != "":
        lead["unique_identifier"] = lead_id

    data = calculate_quote(lead_id, post_data)
    if "contact" in lead:
        data["contact"] = lead["contact"]
    data["data"]["upload_folder_id_roof"] = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Uploads/Dachbilder")
    data["data"]["upload_link_roof"] = f"https://keso.bitrix24.de/docs/path/Auftragsordner/Vorgang {lead['unique_identifier']}/Uploads/Dachbilder"
    data["data"]["upload_folder_id_roof_extra"] = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Uploads/Weitere Dachbilder")
    data["data"]["upload_link_roof_extra"] = f"https://keso.bitrix24.de/docs/path/Auftragsordner/Vorgang {lead['unique_identifier']}/Uploads/Weitere Dachbilder"
    data["data"]["upload_folder_id_electric"] = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Uploads/Elektrik-Bilder")
    data["data"]["upload_link_electric"] = f"https://keso.bitrix24.de/docs/path/Auftragsordner/Vorgang {lead['unique_identifier']}/Uploads/Elektrik-Bilder"
    data["data"]["upload_folder_id_heating"] = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Uploads/Heizungsbilder")
    data["data"]["upload_link_heating"] = f"https://keso.bitrix24.de/docs/path/Auftragsordner/Vorgang {lead['unique_identifier']}/Uploads/Heizungsbilder"
    data["data"]["upload_folder_id_invoices"] = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Uploads/Rechnung vom bisherigem Anbieter")
    data["data"]["upload_link_invoices"] = f"https://keso.bitrix24.de/docs/path/Auftragsordner/Vorgang {lead['unique_identifier']}/Uploads/Rechnung vom bisherigem Anbieter"
    data["data"]["upload_folder_id_contract"] = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Uploads/Vertragsunterlagen")
    data["data"]["upload_link_contract"] = f"https://keso.bitrix24.de/docs/path/Auftragsordner/Vorgang {lead['unique_identifier']}/Uploads/Vertragsunterlagen"
    history = QuoteHistory(
        lead_id=lead_id,
        datetime=datetime.datetime.now(),
        label="",
        data=data,
        is_complete=True
    )
    db.session.add(history)
    db.session.flush()
    history_data = json.loads(json.dumps(history.data))
    history_data["number"] = f"AG-{lead_id}/{history.id}"
    if "is_new_building" in post_data:
        history.data["data"]["is_new_building"] = post_data["is_new_building"]
        if post_data["is_new_building"] is True:
            history.data["data"]["power_meter_number"] = "NEUBAU"
            history.data["data"]["main_malo_id"] = "NEUBAU"
            history.data["data"]["heatcloud_power_meter_number"] = "NEUBAU"
    history.data = history_data
    db.session.commit()
    update_data = {
        "unique_identifier": str(lead_id),
        "upload_link_roof": data["data"]["upload_link_roof"],
        "upload_link_electric": data["data"]["upload_link_electric"],
        "upload_link_heating": data["data"]["upload_link_heating"],
        "upload_link_invoices": data["data"]["upload_link_invoices"],
        "upload_link_contract": data["data"]["upload_link_contract"],
        "is_splittable": "1",
        "has_pv_quote": 0,
        "pv_quote_sum": 0,
        "has_roof_reconstruction_quote": 0,
        "roof_reconstruction_quote_sum": 0,
        "has_heating_quote": 0,
        "heating_quote_sum": 0,
        "has_bluegen_quote": 0,
        "bluegen_quote_sum": 0,
        "has_aircondition_quote": 0,
        "aircondition_quote_sum": 0
    }
    if contact_id is not None:
        update_data["contact_id"] = contact_id

    if "has_pv_quote" in data["data"] and data["data"]["has_pv_quote"] and data.get("total") not in [None, "", 0]:
        quote = add_quote({
            "title": f"PV {lead['contact']['first_name']} {lead['contact']['last_name']}, {lead['contact']['city']}",
            "currency_id": "EUR",
            "opportunity": data["total"],
            "tax_value": data["total_tax"],
            "contact_id": lead["contact_id"],
            "assigned_by_id": lead["assigned_by_id"],
            "lead_id": lead_id,
            "quote_number": history_data["number"],
            "history_id": history.id,
            "unique_identifier": str(lead_id),
            "special_conditions": data["data"].get("special_conditions_pv_quote", None)
        })
        update_quote_products(quote["id"], data)
        update_data["has_pv_quote"] = 1
        update_data["pv_quote_sum"] = history.data.get("total")
    if "has_roof_reconstruction_quote" in data["data"] and data["data"]["has_roof_reconstruction_quote"]:
        quote = add_quote({
            "title": f"Dachsanierung {lead['contact']['first_name']} {lead['contact']['last_name']}, {lead['contact']['city']}",
            "currency_id": "EUR",
            "opportunity": data["roof_reconstruction_quote"]["total"],
            "tax_value": data["roof_reconstruction_quote"]["total_tax"],
            "contact_id": lead["contact_id"],
            "assigned_by_id": lead["assigned_by_id"],
            "lead_id": lead_id,
            "quote_number": history_data["number"],
            "history_id": history.id,
            "unique_identifier": str(lead_id),
            "special_conditions": data["data"].get("special_conditions_roof_reconstruction_quote", None)
        })
        update_quote_products(quote["id"], data["roof_reconstruction_quote"])
        update_data["has_roof_reconstruction_quote"] = 1
        update_data["roof_reconstruction_quote_sum"] = history.data.get("roof_reconstruction_quote").get("total")
    if "has_heating_quote" in data["data"] and data["data"]["has_heating_quote"]:
        quote = add_quote({
            "title": f"Heizung {lead['contact']['first_name']} {lead['contact']['last_name']}, {lead['contact']['city']}",
            "currency_id": "EUR",
            "opportunity": data["heating_quote"]["total"],
            "tax_value": data["heating_quote"]["total_tax"],
            "contact_id": lead["contact_id"],
            "assigned_by_id": lead["assigned_by_id"],
            "lead_id": lead_id,
            "quote_number": history_data["number"],
            "history_id": history.id,
            "unique_identifier": str(lead_id),
            "special_conditions": data["data"].get("special_conditions_heating_quote", "")
        })
        update_quote_products(quote["id"], data["heating_quote"])
        update_data["has_heating_quote"] = 1
        update_data["heating_quote_sum"] = history.data.get("heating_quote").get("total")
    if "has_bluegen_quote" in data["data"] and data["data"]["has_bluegen_quote"]:
        quote = add_quote({
            "title": f"BlueGen {lead['contact']['first_name']} {lead['contact']['last_name']}, {lead['contact']['city']}",
            "currency_id": "EUR",
            "opportunity": data["bluegen_quote"]["total"],
            "tax_value": data["bluegen_quote"]["total_tax"],
            "contact_id": lead["contact_id"],
            "assigned_by_id": lead["assigned_by_id"],
            "lead_id": lead_id,
            "quote_number": history_data["number"],
            "history_id": history.id,
            "unique_identifier": str(lead_id),
            "special_conditions": data["data"].get("special_conditions_bluegen_quote", "")
        })
        update_quote_products(quote["id"], data["bluegen_quote"])
        update_data["has_bluegen_quote"] = 1
        update_data["bluegen_quote_sum"] = history.data.get("bluegen_quote").get("total")
    update_data["has_aircondition_quote"] = 0
    update_data["aircondition_quote_sum"] = 0
    update_lead(lead_id, update_data)
    deal_id = history_data["data"].get("deal_id")
    if deal_id not in [None, 0, ""]:
        deal = get_deal(deal_id)
        if deal is not None:
            update_deal(deal.get("id"), {
                "is_splittable": update_data["is_splittable"],
                "has_pv_quote": update_data["has_pv_quote"],
                "pv_quote_sum": update_data["pv_quote_sum"],
                "has_roof_reconstruction_quote": update_data["has_roof_reconstruction_quote"],
                "roof_reconstruction_quote_sum": update_data["roof_reconstruction_quote_sum"],
                "has_heating_quote": update_data["has_heating_quote"],
                "heating_quote_sum": update_data["heating_quote_sum"],
                "has_bluegen_quote": update_data["has_bluegen_quote"],
                "bluegen_quote_sum": update_data["bluegen_quote_sum"],
                "has_aircondition_quote": update_data["has_aircondition_quote"],
                "aircondition_quote_sum": update_data["aircondition_quote_sum"]
            })
    data["quote_datetime"] = data["datetime"]

    return {"status": "success", "data": data}


@blueprint.route("/<lead_id>/extra_data", methods=['PUT'])
@log_request
def quote_calculator_extra_data_update(lead_id):
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return Response(
            '{"status": "error", "error_code": "not_authorized", "message": "user not authorized for this action"}',
            status=501,
            mimetype='application/json')
    post_data = None
    try:
        post_data = request.json
    except Exception as e:
        pass
    lead_id = int(lead_id)
    if lead_id <= 0:
        return Response(
            '{"status": "error", "error_code": "not_deal_given", "message": "deal id missing in data object"}',
            status=404,
            mimetype='application/json')
    history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    history.data = json.loads(json.dumps(history.data))
    if "power_meter_number" in post_data:
        history.data["data"]["power_meter_number"] = post_data["power_meter_number"]
    if "main_malo_id" in post_data:
        history.data["data"]["main_malo_id"] = post_data["main_malo_id"]
    if "heatcloud_power_meter_number" in post_data:
        history.data["data"]["heatcloud_power_meter_number"] = post_data["heatcloud_power_meter_number"]
    if "is_new_building" in post_data:
        history.data["data"]["is_new_building"] = post_data["is_new_building"]
        if post_data["is_new_building"] is True:
            history.data["data"]["power_meter_number"] = "NEUBAU"
            history.data["data"]["main_malo_id"] = "NEUBAU"
            history.data["data"]["heatcloud_power_meter_number"] = "NEUBAU"
    if "birthdate" in post_data:
        history.data["data"]["birthdate"] = post_data["birthdate"]
    if "iban" in post_data:
        history.data["data"]["iban"] = post_data["iban"]
    if "bic" in post_data:
        history.data["data"]["bic"] = post_data["bic"]
    if "bankname" in post_data:
        history.data["data"]["bankname"] = post_data["bankname"]
    if "extra_notes" in post_data:
        history.data["data"]["extra_notes"] = post_data["extra_notes"]
    for index, consumer in enumerate(post_data["consumers"]):
        if "power_meter_number" in consumer:
            history.data["data"]["consumers"][index]["power_meter_number"] = consumer["power_meter_number"]
        if "malo_id" in consumer:
            history.data["data"]["consumers"][index]["malo_id"] = consumer["malo_id"]
    db.session.commit()
    return {"status": "success", "data": history.data}


@blueprint.route("/<lead_id>/cloud_pdfs", methods=['PUT'])
@log_request
def quote_calculator_cloud_pdfs(lead_id):
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return Response(
            '{"status": "error", "error_code": "not_authorized", "message": "user not authorized for this action"}',
            status=501,
            mimetype='application/json')
    lead_id = int(lead_id)
    if lead_id <= 0:
        return Response(
            '{"status": "error", "error_code": "not_deal_given", "message": "deal id missing in data object"}',
            status=404,
            mimetype='application/json')
    return quote_calculator_cloud_pdfs_action(lead_id)


def quote_calculator_cloud_pdfs_action(lead_id):
    from app.modules.offer.services.pdf_generation.cloud_offer import generate_cloud_pdf
    from app.modules.offer.services.pdf_generation.feasibility_study import generate_feasibility_study_pdf, generate_feasibility_study_short_pdf
    from app.modules.importer.sources.bitrix24._association import find_association

    lead = get_lead(lead_id)
    lead_link = find_association("Lead", remote_id=lead_id)
    reseller_link = None
    if "assigned_by_id" in lead and lead["assigned_by_id"] is not None and lead["assigned_by_id"] != "":
        reseller_link = find_association("Reseller", remote_id=lead["assigned_by_id"])
    history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    folder_id = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Angebote/Version {history.id}")
    calculated = history.data["calculated"]
    data = history.data["data"]
    data["heating_quote"] = history.data["heating_quote"]
    if "contact" in history.data:
        data["address"] = history.data["contact"]
    if "contact" in lead:
        data["address"] = lead["contact"]
    data["total_net"] = history.data["total_net"]
    data["tax_rate"] = history.data["tax_rate"]
    items = get_cloud_products(data={"calculated": calculated, "data": data})
    offer_v2_data = {
        "reseller_id": None,
        "offer_group": "cloud-offer",
        "datetime": datetime.datetime.now(),
        "currency": "eur",
        "tax_rate": data["tax_rate"],
        "lead_id": None,
        "subtotal": calculated["cloud_price"],
        "subtotal_net": calculated["cloud_price"] / (1 + data["tax_rate"] / 100),
        "shipping_cost": 0,
        "shipping_cost_net": 0,
        "discount_total": 0,
        "total_tax": calculated["cloud_price"] * (data["tax_rate"] / 100),
        "total": calculated["cloud_price"],
        "status": "created",
        "data": data,
        "calculated": calculated,
        "items": items,
        "customer_raw": {}
    }
    if reseller_link is not None:
        offer_v2_data["reseller_id"] = reseller_link.local_id
    if lead_link is not None:
        offer_v2_data["lead_id"] = lead_link.local_id
    if "email" in lead and len(lead["email"]) > 0:
        offer_v2_data["customer_raw"]["email"] = lead["email"][0]["VALUE"]
    if "address" in data and "lastname" in data["address"]:
        offer_v2_data["customer_raw"]["firstname"] = data["address"]["firstname"]
        offer_v2_data["customer_raw"]["lastname"] = data["address"]["lastname"]
        offer_v2_data["customer_raw"]["default_address"] = data["address"]
        if "company" in data["address"]:
            offer_v2_data["customer_raw"]["company"] = data["address"]["company"]
    item = add_item_v2(data=offer_v2_data)
    history_data = json.loads(json.dumps(history.data))
    history_data["data"]["cloud_number"] = item.number
    history_data["calculated"]["cloud_number"] = item.number
    history_data["cloud_number"] = item.number
    item = OfferV2.query.get(item.id)
    if history_data["data"].get("cloud_quote_type") not in ["no-cloud"]:
        if item.pdf is None:
            generate_cloud_pdf(item)
        history_data["calculated"]["pdf_link"] = item.pdf.longterm_public_link
        history_data["pdf_link"] = history_data["calculated"]["pdf_link"]
        history_data["pdf_cloud_config_file_id"] = item.pdf.bitrix_file_id
    deal = None
    deal_id = history_data["data"].get("deal_id")
    if deal_id not in [None, 0, ""]:
        deal = get_deal(deal_id)
    if history_data["data"].get("cloud_quote_type") not in ["followup_quote", "interim_quote"]:
        if item.feasibility_study_pdf is None:
            generate_feasibility_study_pdf(item)
        history_data["calculated"]["pdf_wi_link"] = item.feasibility_study_pdf.longterm_public_link
        history_data["pdf_wi_link"] = history_data["calculated"]["pdf_wi_link"]
        history_data["pdf_wi_file_id"] = item.feasibility_study_pdf.bitrix_file_id
    if history_data["data"].get("cloud_quote_type") in ["followup_quote", "interim_quote"] or (deal is not None and deal.get("category_id") in ["15", "176"]):
        contract_number = None
        deal = None
        if history_data.get("data").get("deal_id") not in [None, 0, ""]:
            deal = get_deal(history_data.get("data").get("deal_id"))
            contract_number = deal.get("contract_number")
        insign_token = encode_jwt({
            "deal_id": history_data.get("data").get("deal_id"),
            "contract_number": contract_number,
            "cloud_number": history_data.get("cloud_number")
        }, expire_minutes=90*24*60)
        if deal is not None:
            update_deal(deal.get("id"), {
                "cloud_follow_quote_link": history_data["pdf_link"],
                "cloud_follow_quote_insign_link": f"https://api.korbacher-energiezentrum.de/sign/{insign_token['token']}"
            })
    history.data = history_data
    db.session.commit()
    return {"status": "success", "data": history.data}


@blueprint.route("/<lead_id>/pv_pdf", methods=['PUT'])
@log_request
def quote_calculator_pv_pdf(lead_id):
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return Response(
            json.dumps({"status": "failed"}),
            status=200,
            mimetype='application/json')
    lead = get_lead(lead_id)
    history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    data = json.loads(json.dumps(history.data))

    subfolder_id = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Angebote/Version {history.id}")

    genrate_pdf(data, generate_quote_pdf, lead_id, "pdf_pv_file_id", "PV-Angebot.pdf", subfolder_id)

    history.data = data
    db.session.commit()
    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


@blueprint.route("/<lead_id>/heating_pdf", methods=['PUT'])
@log_request
def quote_calculator_heating_pdf(lead_id):
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return Response(
            json.dumps({"status": "failed"}),
            status=200,
            mimetype='application/json')
    data = quote_calculator_heating_pdf_action(lead_id)
    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


def quote_calculator_heating_pdf_action(lead_id):
    lead = get_lead(lead_id)
    history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    data = json.loads(json.dumps(history.data))

    subfolder_id = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Angebote/Version {history.id}")

    genrate_pdf(data, generate_heating_pdf, lead_id, "pdf_heating_file_id", "Heizung-Angebot.pdf", subfolder_id)

    history.data = data
    db.session.commit()
    return data


@blueprint.route("/<lead_id>/bluegen_pdf", methods=['PUT'])
@log_request
def quote_calculator_bluegen_pdf(lead_id):
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return Response(
            json.dumps({"status": "failed"}),
            status=200,
            mimetype='application/json')
    lead = get_lead(lead_id)
    history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    data = json.loads(json.dumps(history.data))

    subfolder_id = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Angebote/Version {history.id}")

    genrate_pdf(data, generate_bluegen_pdf, lead_id, "pdf_bluegen_file_id", "Bluegen-Angebot.pdf", subfolder_id)
    genrate_pdf(data, generate_bluegen_wi_pdf, lead_id, "pdf_bluegen_wi_file_id", "Bluegen-WI.pdf", subfolder_id)

    history.data = data
    db.session.commit()
    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


@blueprint.route("/<lead_id>/roof_reconstruction_pdf", methods=['PUT'])
@log_request
def quote_calculator_roof_reconstruction_pdf(lead_id):
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return Response(
            json.dumps({"status": "failed"}),
            status=200,
            mimetype='application/json')
    lead = get_lead(lead_id)
    history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    data = json.loads(json.dumps(history.data))

    subfolder_id = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Angebote/Version {history.id}")

    genrate_pdf(data, generate_roof_reconstruction_pdf, lead_id, "pdf_roof_file_id", "Dach-Angebot.pdf", subfolder_id)

    history.data = data
    db.session.commit()
    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


@blueprint.route("/<lead_id>/commission_pdf", methods=['PUT'])
@log_request
def quote_calculator_commission_pdf(lead_id):
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return Response(
            json.dumps({"status": "failed"}),
            status=200,
            mimetype='application/json')
    lead = get_lead(lead_id)
    history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    data = json.loads(json.dumps(history.data))

    subfolder_id = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Angebote/Version {history.id}")

    genrate_pdf(data, generate_commission_pdf, lead_id, "pdf_commission_file_id", "Provision.pdf", subfolder_id)
    data["pdf_commission_link"] = get_public_link(data["pdf_commission_file_id"])

    history.data = data
    db.session.commit()
    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


@blueprint.route("/<lead_id>/datasheets_pdf", methods=['PUT'])
@log_request
def quote_calculator_datasheets_pdf(lead_id):
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return Response(
            json.dumps({"status": "failed"}),
            status=200,
            mimetype='application/json')
    data = quote_calculator_datasheets_pdf_action(lead_id)
    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


def quote_calculator_datasheets_pdf_action(lead_id):
    lead = get_lead(lead_id)
    history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    data = json.loads(json.dumps(history.data))
    subfolder_id = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Angebote/Version {history.id}")

    genrate_pdf(data, generate_datasheet_pdf, lead_id, "pdf_datasheets_file_id", "Datenblaetter.pdf", subfolder_id)
    data["pdf_datasheets_link"] = get_public_link(data["pdf_datasheets_file_id"])

    history.data = data
    db.session.commit()
    update_lead(lead_id, {"pdf_datasheets_link": data["pdf_datasheets_link"]})
    return data


@blueprint.route("/<lead_id>/summary_pdf", methods=['PUT', 'GET'])
@log_request
def quote_calculator_summary_pdf(lead_id):
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return Response(
            json.dumps({"status": "failed"}),
            status=200,
            mimetype='application/json')
    data = quote_calculator_summary_pdf_action(lead_id)
    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


def quote_calculator_summary_pdf_action(lead_id):
    lead = get_lead(lead_id)
    history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    data = json.loads(json.dumps(history.data))
    subfolder_id = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Angebote/Version {history.id}")

    genrate_pdf(data, generate_cover_pdf, lead_id, "pdf_cover_file_id", "Deckblatt.pdf", subfolder_id)
    genrate_pdf(data, generate_letter_pdf, lead_id, "pdf_letter_file_id", "Anschreiben.pdf", subfolder_id)
    genrate_pdf(data, generate_summary_pdf, lead_id, "pdf_summary_file_id", "Energiemappe.pdf", subfolder_id)
    data["pdf_summary_link"] = get_public_link(data["pdf_summary_file_id"])
    if "has_heating_quote" in data["data"] and data["data"]["has_heating_quote"]:
        genrate_pdf(data, generate_contract_summary_part4_pdf, lead_id, "pdf_contract_summary_part4_file_id", "Heizungskonzept.pdf", subfolder_id)
        data["pdf_contract_summary_part4_file_link"] = get_public_link(data["pdf_contract_summary_part4_file_id"])

    history.data = data
    db.session.commit()
    update_lead(lead_id, {
        "pdf_summary_link": data["pdf_summary_link"]
    })
    deal = None
    deal_id = history.data["data"].get("deal_id")
    if deal_id not in [None, 0, ""]:
        deal = get_deal(deal_id)
    if deal is not None and deal.get("category_id") in ["239"]:
        update_deal(deal.get("id"), {
            "pdf_datasheets_link": data.get("pdf_datasheets_link"),
            "pdf_summary_link": data.get("pdf_summary_link"),
            "pdf_quote_summary_link": data.get("pdf_quote_summary_link"),
            "pdf_contract_summary_link": data.get("pdf_contract_summary_link")
        })

    return data


@blueprint.route("/<lead_id>/quote_summary_pdf", methods=['PUT'])
@log_request
def quote_calculator_quote_summary_pdf(lead_id):
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return Response(
            json.dumps({"status": "failed"}),
            status=200,
            mimetype='application/json')
    data = quote_calculator_quote_summary_pdf_action(lead_id)
    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


def quote_calculator_quote_summary_pdf_action(lead_id):
    lead = get_lead(lead_id)
    history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    data = json.loads(json.dumps(history.data))
    subfolder_id = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Angebote/Version {history.id}")

    genrate_pdf(data, generate_quote_summary_pdf, lead_id, "pdf_quote_summary_file_id", "Angebote.pdf", subfolder_id)
    data["pdf_quote_summary_link"] = get_public_link(data["pdf_quote_summary_file_id"])

    history.data = data
    db.session.commit()
    update_lead(lead_id, {
        "automatic_checked": 0 if data["has_special_condition"] is True else 1,
        "info_roof": data["data"].get("extra_notes"),
        "info_electric": data["data"].get("extra_notes"),
        "info_heating": data["data"].get("extra_notes"),
        "construction_week": data["construction_week"],
        "construction_year": data["construction_year"],
        "pdf_quote_summary_link": data["pdf_quote_summary_link"]
    })
    return data


@blueprint.route("/<lead_id>/contract_summary_pdf", methods=['PUT'])
@log_request
def quote_calculator_contract_summary_pdf(lead_id):
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return Response(
            json.dumps({"status": "failed"}),
            status=200,
            mimetype='application/json')
    data = quote_calculator_contract_summary_pdf_action(lead_id)

    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


def quote_calculator_contract_summary_pdf_action(lead_id):
    lead = get_lead(lead_id)
    history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    data = json.loads(json.dumps(history.data))
    subfolder_id = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Angebote/Version {history.id}")

    genrate_pdf(data, generate_contract_summary_part1_pdf, lead_id, "pdf_contract_summary_part1_file_id", "Verkaufsunterlagen.pdf", subfolder_id)
    genrate_pdf(data, generate_contract_summary_part2_pdf, lead_id, "pdf_contract_summary_part2_file_id", "Abtrettung.pdf", subfolder_id)
    genrate_pdf(data, generate_contract_summary_part3_pdf, lead_id, "pdf_contract_summary_part3_file_id", "Contracting.pdf", subfolder_id)
    if "has_pv_quote" in data["data"] and data["data"]["has_pv_quote"]:
        genrate_pdf(data, generate_contract_summary_part4_1_pdf, lead_id, "pdf_contract_summary_part4_1_file_id", "Technischer Aufnahmebogen.pdf", subfolder_id)
        data["pdf_contract_summary_part4_1_file_link"] = get_public_link(data["pdf_contract_summary_part4_1_file_id"])
    if "has_heating_quote" in data["data"] and data["data"]["has_heating_quote"]:
        genrate_pdf(data, generate_contract_summary_part5_pdf, lead_id, "pdf_contract_summary_part5_file_id", "Contracting WP.pdf", subfolder_id)
    genrate_pdf(data, generate_contract_summary_pdf, lead_id, "pdf_contract_summary_file_id", "Vertragsunterlagen.pdf", subfolder_id)
    data["pdf_contract_summary_link"] = get_public_link(data["pdf_contract_summary_file_id"])
    data["pdf_contract_summary_link_datetime"] = str(datetime.datetime.now())

    history.data = data
    db.session.commit()
    lead_update_data = {"pdf_contract_summary_link": data["pdf_contract_summary_link"]}
    if "pdf_contract_summary_part4_file_link" in data:
        lead_update_data["heatpump_concept_link"] = data["pdf_contract_summary_part4_file_link"]
    else:
        lead_update_data["heatpump_concept_link"] = ""
    lead_update_data["contracting_version"] = "Version F1"
    if datetime.datetime.now() >= datetime.datetime(2021,12,14,0,0,0):
        lead_update_data["contracting_version"] = "Version G1"
    update_lead(lead_id, lead_update_data)
    return data


@blueprint.route("/<lead_id>/heatpump_autogenerate_pdf", methods=['PUT'])
@log_request
def quote_calculator_heatpump_autogenerate_pdf(lead_id):
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return Response(
            json.dumps({"status": "failed"}),
            status=200,
            mimetype='application/json')
    data = quote_calculator_heatpump_autogenerate_pdf_action(lead_id)

    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


def quote_calculator_heatpump_autogenerate_pdf_action(lead_id):
    lead = get_lead(lead_id)
    history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    data = json.loads(json.dumps(history.data))
    subfolder_id = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Angebote/Version {history.id}")

    genrate_pdf(data, generate_heatpump_auto_generate_pdf, lead_id, "pdf_heatpump_auto_generate_file_id", "Angebotspaket Heizung.pdf", subfolder_id)
    data["pdf_heatpump_auto_generate_link"] = get_public_link(data["pdf_heatpump_auto_generate_file_id"])

    history.data = data
    db.session.commit()
    lead_update_data = {"pdf_heatpump_auto_generate_link": data["pdf_heatpump_auto_generate_link"]}
    update_lead(lead_id, lead_update_data)
    return data


@blueprint.route("/<lead_id>/contract_summary_pdf3", methods=['GET'])
@log_request
def quote_calculator_contract_summary_pdf3(lead_id):
    history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    data = json.loads(json.dumps(history.data))

    pdf = generate_contract_summary_part4_1_pdf(lead_id, data, return_string=True)

    return Response(pdf,
        status=200)
        #mimetype='application/pdf')


def genrate_pdf(data, generate_function, lead_id, pdf_id_key, label, subfolder_id, order_confirmation=False):
    if order_confirmation:
        pdf = generate_function(lead_id, data, order_confirmation=order_confirmation)
        pdf_id_key = pdf_id_key.replace("pdf_", "pdf_confirmation_")
        label = "AB " + label
    else:
        pdf = generate_function(lead_id, data)
    if pdf is None:
        return Response(
            '{"status": "error", "error_code": "pdf_generation_failed", "message": "pdf generation failed: ' + label + '"}',
            status=404,
            mimetype='application/json')
    data[pdf_id_key] = add_file(folder_id=subfolder_id, data={
        "file_content": pdf,
        "filename": label
    })
    if data[pdf_id_key] is None or data[pdf_id_key] <= 0:
        return Response(
            '{"status": "error", "error_code": "drive_upload_failed", "message": "bitrix drive upload failed"}',
            status=404,
            mimetype='application/json')


@blueprint.route("/insign/callback/<token>", methods=['GET', 'POST'])
@log_request
def get_insign_callback(token):
    from app.modules.external.insign.signature import download_file

    config = get_settings("external/bitrix24/folder_creation")
    token_data = decode_jwt(token)
    session_id = request.args.get("sessionid")
    event_type = request.args.get("eventid")
    if event_type != "EXTERNBEARBEITUNGFERTIG":
        return Response(
            '{"status": "error", "error_code": "drive_upload_failed", "message": "bitrix drive upload failed"}',
            status=200,
            mimetype='application/json')

    myprotal_folder = next((item for item in config["folders"] if item["key"] == "drive_myportal_folder"), None)
    lead = get_lead(token_data["unique_identifier"])
    customer_folder_id = get_folder_id(myprotal_folder["folder_id"], path=f"Kunde {lead['contact_id']}/Vertragsunterlagen")
    collection_files = []
    heatpump_survey_link = None
    contracting_heatpump_link = None
    for file in token_data.get("documents", []):
        file_content = download_file(sessionId=session_id, file_id=file["id"])
        if isinstance(file_content, dict):
            error_response = json.dumps({
                "status": "error",
                "error_code": "document_download_failed",
                "message": f"GET /get/document s:{session_id} d:{file['id']} did respond with error in data",
                "data": file_content
            }, indent=2)
            return Response(
                error_response,
                status=400,
                mimetype='application/json')
        else:
            '''add_file(0, {
                "bitrix_file_id": file["id"],
                "filename": file["displayname"],
                "file_content": file_content
            })'''
            if file["displayname"] == "Technischer Aufnahmebogen" and token_data.get("upload_folder_id_tab") not in [None, "", 0]:
                add_file(token_data["upload_folder_id_tab"], {
                    "filename": f'{file["displayname"]} ({token_data["number"]}).pdf',
                    "file_content": file_content
                })
            add_file(customer_folder_id, {
                "filename": token_data["number"] + " " + file["displayname"] + ".pdf",
                "file_content": file_content
            })
            if file["displayname"] == "Heizungskonzept":
                file_id = add_file(token_data["upload_folder_id_heating"], {
                    "filename": token_data["number"] + " " + file["displayname"] + ".pdf",
                    "file_content": file_content
                })
                heatpump_survey_link = get_public_link(file_id, 518400)
            file_id = add_file(token_data["upload_folder_id_contract"], {
                "filename": token_data["number"] + " " + file["displayname"] + ".pdf",
                "file_content": file_content
            })
            if file["displayname"] == "Contractigvertrag WP":
                contracting_heatpump_link = get_public_link(file_id, 518400)
            if file_id is not None:
                collection_files.append({
                    "id": file_id,
                    "filename": file["displayname"] + ".pdf"
                })
    if len(collection_files) > 0:
        jwt = encode_shared_jwt(data={
            "files": collection_files
        }, expire_minutes=365*24*60)
        lead_data = {
            "collection_url": f"https://kunden.energie360.de/files/collection?token={jwt['token']}",
            "zoom_appointment": str(datetime.datetime.now()),
            "zoom_link": "1"
        }
        if contracting_heatpump_link is not None:
            lead_data["contracting_heatpump_link"] = contracting_heatpump_link
        if heatpump_survey_link is not None:
            lead_data["heatpump_survey_link"] = heatpump_survey_link
        if "pv_quote_sum_net" in token_data:
            if token_data["pv_quote_sum_net"] is None:
                lead_data["pv_quote_sum_net"] = 0
            else:
                lead_data["pv_quote_sum_net"] = f'{token_data["pv_quote_sum_net"]}|EUR'
        if "heating_quote_sum_net" in token_data:
            if token_data["heating_quote_sum_net"] is None:
                lead_data["heating_quote_sum_net"] = 0
            else:
                lead_data["heating_quote_sum_net"] = f'{token_data["heating_quote_sum_net"]}|EUR'
        if "bluegen_quote_sum_net" in token_data:
            if token_data["bluegen_quote_sum_net"] is None:
                lead_data["bluegen_quote_sum_net"] = 0
            else:
                lead_data["bluegen_quote_sum_net"] = f'{token_data["bluegen_quote_sum_net"]}|EUR'
        if "roof_reconstruction_quote_sum_net" in token_data:
            if token_data["bluegen_quote_sum_net"] is None:
                lead_data["roof_reconstruction_quote_sum_net"] = 0
            else:
                lead_data["roof_reconstruction_quote_sum_net"] = f'{token_data["roof_reconstruction_quote_sum_net"]}|EUR'
        if "pv_kwp" in token_data:
            lead_data["pv_kwp"] = token_data["pv_kwp"]
        if lead.get("automatic_checked") in ["1", True, 1]:
            lead_data["order_confirmation_date"] = str(datetime.datetime.now())
        lead_data["order_sign_date"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S-01:00")
        update_lead(token_data["unique_identifier"], lead_data)
        if token_data.get("deal_id") not in [None, 0, "", "0", "None"]:
            update_deal(token_data.get("deal_id"), lead_data)

    log = InsignLog.query.filter(InsignLog.session_id == session_id).first()
    if log is not None:
        data = json.loads(json.dumps(log.data))
        data["final_response"] = str(datetime.datetime.now())
        log.data = data
        db.session.commit()
    return Response(
            '{"status": "error", "error_code": "drive_upload_failed", "message": "bitrix drive upload failed"}',
            status=200,
            mimetype='application/json')


@blueprint.route("/<lead_id>/insign/data", methods=['POST'])
@log_request
def get_insign_data(lead_id):
    from app.modules.external.insign.signature import get_public_url

    auth_info = get_auth_info()
    if auth_info is not None and auth_info["domain_raw"] == "keso.bitrix24.de":
        lead_id = int(lead_id)
        history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).filter(QuoteHistory.is_complete.is_(True)).order_by(QuoteHistory.datetime.desc()).first()
        data = json.loads(json.dumps(history.data))
        sessionId = get_insign_session(data)
        try:
            email = data["contact"]["email"][0]["VALUE"]
        except Exception as e:
            email = "platzhalter@energie360.de"
        public_url = get_public_url(sessionId, email)
        return Response(
            json.dumps({"status": "success", "data": {"url": public_url}}),
            status=200,
            mimetype='application/json')
    return Response(
        '{"status": "error", "error_code": "not_authorized", "message": "user not authorized for this action"}',
        status=501,
        mimetype='application/json')


@blueprint.route("/<lead_id>/insign/email", methods=['POST'])
@log_request
def send_insign_email(lead_id):
    from app.modules.external.insign.signature import send_insign_email

    auth_info = get_auth_info()
    if auth_info is not None and auth_info["domain_raw"] == "keso.bitrix24.de":
        lead_id = int(lead_id)
        history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
        data = json.loads(json.dumps(history.data))
        sessionId = get_insign_session(data)
        return Response(
            json.dumps({
                "status": "success",
                "data": send_insign_email(sessionId, data["contact"]["email"][0]["VALUE"])
            }),
            status=200,
            mimetype='application/json')
    return Response(
        '{"status": "error", "error_code": "not_authorized", "message": "user not authorized for this action"}',
        status=501,
        mimetype='application/json')


def get_insign_session(data):
    from app.modules.external.insign.signature import get_session_id
    from app.utils.jinja_filters import numberformat
    config = get_settings("general")
    signatures = [
        {
            "id": "mainsig",
            "displayname": "Unterschrift",
            "textsearch": f"__main_sig__",
            "required": True
        }
    ]
    documents = []
    prefillable_documents = []
    if "pdf_pv_file_id" in data and data["pdf_pv_file_id"] > 0:
        documents.append({
            "id": data["pdf_pv_file_id"],
            "displayname": "PV-Angebot",
            "signatures": signatures
        })
    if "pdf_cloud_config_file_id" in data and data["pdf_cloud_config_file_id"] > 0:
        documents.append({
            "id": data["pdf_cloud_config_file_id"],
            "displayname": "Cloud-Angebot",
            "signatures": signatures
        })
    if "pdf_heating_file_id" in data and data["pdf_heating_file_id"] > 0:
        documents.append({
            "id": data["pdf_heating_file_id"],
            "displayname": "Heizung-Angebot",
            "signatures": signatures
        })
    if "pdf_roof_file_id" in data and data["pdf_roof_file_id"] > 0:
        documents.append({
            "id": data["pdf_roof_file_id"],
            "displayname": "Dach-Angebot",
            "signatures": signatures
        })
    if "pdf_bluegen_file_id" in data and data["pdf_bluegen_file_id"] > 0:
        documents.append({
            "id": data["pdf_bluegen_file_id"],
            "displayname": "Bluegen-Angebot",
            "signatures": signatures
        })
    if "pdf_contract_summary_part4_1_file_id" in data:
        prefillable_documents.append({
            "id": data["pdf_contract_summary_part4_1_file_id"],
            "displayname": "Technischer Aufnahmebogen",
            "preFilledFields": [],
            "signatures": signatures
        })
    if "pdf_contract_summary_part4_file_id" in data:
        prefillable_documents.append({
            "id": data["pdf_contract_summary_part4_file_id"],
            "displayname": "Heizungskonzept",
            "preFilledFields": [],
            "signatures": signatures
        })
    if "pdf_contract_summary_part5_file_id" in data:
        prefillable_documents.append({
            "id": data["pdf_contract_summary_part5_file_id"],
            "displayname": "Contractigvertrag WP",
            "preFilledFields": [],
            "signatures": signatures
        })
    prefillable_documents.append({
        "id": data["pdf_contract_summary_part2_file_id"],
        "displayname": "Abrettungsformular",
        "preFilledFields": []
    })
    prefillable_documents.append({
        "id": data["pdf_contract_summary_part1_file_id"],
        "displayname": "Verkaufsunterlagen",
        "preFilledFields": []
    })
    prefillable_documents.append({
        "id": data["pdf_contract_summary_part3_file_id"],
        "displayname": "Contractigvertrag",
        "preFilledFields": []
    })
    prefillable_documents.append({
        "id": 5400174,  # https://keso.bitrix24.de/disk/downloadFile/5400174/?&ncc=1&filename=energie360-vollmacht.pdf
        "displayname": "Maklervollmacht",
        "preFilledFields": []
    })
    auto_fill_fields = [
        { "id": "Name und Vorname", "text": data.get("contact", {}).get("firstname") + " " + data.get("contact", {}).get("lastname") },
        { "id": "name vorname 1", "text": data.get("contact", {}).get("firstname") + " " + data.get("contact", {}).get("lastname") },
        { "id": "Name, Vorname ", "text": data.get("contact", {}).get("firstname") + " " + data.get("contact", {}).get("lastname") },
        { "id": "Name", "text": data.get("contact", {}).get("firstname") + " " + data.get("contact", {}).get("lastname") },
        { "id": "Vorname", "text": data.get("contact", {}).get("firstname") },
        { "id": "Nachname", "text": data.get("contact", {}).get("lastname") },
        { "id": "Strasse", "text": data.get("contact", {}).get("street") },
        { "id": "Hausnummer", "text": data.get("contact", {}).get("street_nb") },
        { "id": "Straße Hausnr", "text": data.get("contact", {}).get("street") + " " + data.get("contact", {}).get("street_nb") },
        { "id": "PLZ", "text": data.get("contact", {}).get("zip") },
        { "id": "Ort", "text": data.get("contact", {}).get("city") },
        { "id": "Wohnort", "text": data.get("contact", {}).get("city") },
        { "id": "Standort", "text": data.get("contact", {}).get("zip") + " " + data.get("contact", {}).get("city") },
        { "id": "PLZ, Ort", "text": data.get("contact", {}).get("zip") + " " + data.get("contact", {}).get("city") },
        { "id": "PLZ Ort", "text": data.get("contact", {}).get("zip") + " " + data.get("contact", {}).get("city") },
        { "id": "Anschrift", "text": data.get("contact", {}).get("street") + " " + data.get("contact", {}).get("street_nb") + " " + data.get("contact", {}).get("zip") + " " + data.get("contact", {}).get("city") },
        { "id": "Kwp Nennleistung", "text": numberformat(data.get("data", {}).get("pv_kwp")) },
        { "id": "IBAN", "text": data.get("data", {}).get("iban") },
        { "id": "BIC", "text": data.get("data", {}).get("bic") },
        { "id": "Zähler Nummer", "text": data.get("data", {}).get("power_meter_number") },
        { "id": "Wärme Zählernummer", "text": data.get("data", {}).get("heatcloud_power_meter_number") },
        { "id": "malo id", "text": data.get("data", {}).get("main_malo_id") },
        { "id": "Geburtsdatum", "text": data.get("data", {}).get("birthdate") }
    ]
    for field in auto_fill_fields:
        for n in range(-1,7):
            suffix = n
            if n == -1:
                suffix = ""
            for document in prefillable_documents:
                document["preFilledFields"].append({
                    "id": f"{field['id']}#{suffix}",
                    "text": field['text']
                })
                document["preFilledFields"].append({
                    "id": f"{field['id']}{suffix}",
                    "text": field['text']
                })

    for document in prefillable_documents:
        documents.append(document)
    token_documents = json.loads(json.dumps(documents))
    for document in token_documents:
        if "preFilledFields" in document:
            del document["preFilledFields"]
    token_data = {
            "unique_identifier": data["id"],
            "deal_id": data.get("data", {}).get("deal_id"),
            "number": data["number"],
            "pv_quote_sum_net": data.get("total_net"),
            "heating_quote_sum_net": data["heating_quote"].get("total_net"),
            "bluegen_quote_sum_net": data["bluegen_quote"].get("total_net"),
            "roof_reconstruction_quote_sum_net": data["roof_reconstruction_quote"].get("total_net"),
            "pv_kwp": None,
            "documents": token_documents,
            "upload_folder_id_tab": data["data"].get("upload_folder_id_tab"),
            "upload_folder_id_electric": data["data"]["upload_folder_id_electric"],
            "upload_folder_id_heating": data["data"]["upload_folder_id_heating"],
            "upload_folder_id_contract": data["data"]["upload_folder_id_contract"]
        }
    if "calculated" in data:
        token_data["pv_kwp"] = data["calculated"].get("pv_kwp")
    token = encode_jwt(token_data, 172800)
    print(json.dumps(documents, indent=2))
    return get_session_id(
        {
            "displayname": data["number"],
            "foruser": data["assigned_by_id"] + " " + data["assigned_user"]["EMAIL"],
            "callbackURL": "https://www.energie360.de/insign-callback/",
            "userFullName": f'{data["assigned_user"]["NAME"]} {data["assigned_user"]["LAST_NAME"]}',
            "userEmail": data["assigned_user"]["EMAIL"],
            "serverSidecallbackURL": f"{config['base_url']}quote_calculator/insign/callback/{token['token']}",
            "documents": documents
        },
        data.get("id")
    )


@blueprint.route("", methods=['GET', 'POST'])
def quote_calculator_index():
    from app.modules.quote_calculator.cron import recreate_quote
    config = get_settings(section="external/bitrix24")
    auth_info = get_auth_info()
    if auth_info["user"] is None:
        return "Forbidden2"
    options = request.form.get("PLACEMENT_OPTIONS")
    if options is None:
        return "Keine Placement Optionen gesetzt"
    options = json.loads(options)
    deal_id = None
    if request.form.get("PLACEMENT") == "CRM_DEAL_DETAIL_TAB":
        deal = get_deal(options["ID"])
        if deal.get("unique_identifier") in [None, ""] and str(deal.get("category_id")) in ["220", "15", "176"]:
            lead = recreate_quote(deal["id"], create_new_quote=False)
            options["ID"] = lead.get("id")
        else:
            options["ID"] = deal["unique_identifier"]
        deal_id = deal.get("id")
    if "ID" not in options:
        return "Keine ID gewählt"
    token = encode_jwt(auth_info, expire_minutes=600)
    return render_template("quote_calculator/quote_calculator.html", token=token, lead_id=options["ID"], deal_id=deal_id)


@blueprint.route("/install", methods=['GET', 'POST'])
def install_quote_calculator():
    env = os.getenv('ENVIRONMENT')
    return render_template("quote_calculator/install.html", domain=request.host, env=env)


@blueprint.route("/uninstall", methods=['POST'])
def uninstall_quote_calculator():
    return render_template("quote_calculator/uninstall.html", domain=request.host)


def is_value_changed(new_value, old_value):
    if new_value is None and old_value is None:
        return False
    if old_value is None:
        return True
    if isinstance(new_value, list):
        if len(new_value) != len(old_value):
            return True
        for index in range(len(new_value)):
            if is_value_changed(new_value[index], old_value[index]):
                return True
    if isinstance(new_value, dict):
        for key in new_value.keys():
            if key not in old_value or is_value_changed(new_value[key], old_value.get(key)):
                return True
    return new_value != old_value


def is_uncalculated_field(fieldname):
    if fieldname is None:
        return True
    if fieldname[:8] == "tab_img_":
        return True
    if fieldname[:9] == "is_valid_":
        return True
    if fieldname in UNCALCULATED_FIELDS:
        return True
    return False


def is_temp_field(fieldname):
    if fieldname[:8] == "tab_img_" and (fieldname[-5:] == "_link" or fieldname[-11:] == "_link_small"):
        return True
    if fieldname[:9] == "is_valid_":
        return True
    return False


def fix_legacy_solar_edge_links():
    updated_leads = []
    histories = QuoteHistory.query.filter(QuoteHistory.datetime > '2023-01-10').order_by(QuoteHistory.datetime.desc()).all()
    for history in histories:
        if history.lead_id not in updated_leads:
            if history.data is not None and history.data.get("data") not in [None] and history.data.get("data").get("solaredge_designer_link") not in [None, ""]:
                updated_leads.append(history.lead_id)
                update_lead(history.lead_id, {
                    "solaredge_designer_link": history.data.get("data").get("solaredge_designer_link")
                })
                print(history.lead_id, history.data.get("data").get("solaredge_designer_link"))


def fix_legacy_copy_tab_pdf():
    from app.modules.external.bitrix24.drive import get_folder, get_file_content
    checked_ids = []
    quotes = QuoteHistory.query.filter(QuoteHistory.datetime > "2023-01-15").filter(QuoteHistory.is_complete.is_(True)).all()
    for quote in quotes:
        if quote.lead_id not in checked_ids:
            checked_ids.append(quote.lead_id)
            print("lead", quote.lead_id)
            folder_id = get_folder_id(parent_folder_id=442678, path=f"Vorgang {quote.lead_id}/Uploads/TAB")
            if folder_id is None:
                continue
            existing_found = False
            files = get_folder(folder_id, force=True)
            for file in files:
                if file["NAME"].find("Technischer Aufnahmebogen") >= 0:
                    existing_found = True
            if existing_found is False:
                folder2_id = get_folder_id(parent_folder_id=442678, path=f"Vorgang {quote.lead_id}/Uploads/Vertragsunterlagen")
                copy_file = None
                files = get_folder(folder2_id, force=True)
                for file in files:
                    if file["NAME"].find("Technischer Aufnahmebogen") >= 0:
                        if copy_file is None or parse(copy_file["UPDATE_TIME"]) < parse(file["UPDATE_TIME"]):
                            copy_file = file
                if copy_file is not None:
                    print("copy file")
                    file_content = get_file_content(copy_file["ID"])
                    add_file(folder_id, {
                        "filename": f'Technischer Aufnahmebogen.pdf',
                        "file_content": file_content
                    })