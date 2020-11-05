import requests
import json
import os
import datetime
from flask import Blueprint, request, render_template, redirect, make_response, Response

from app import db
from app.decorators import api_response
from app.modules.auth import get_auth_info
from app.modules.auth.jwt_parser import decode_jwt, encode_jwt
from app.modules.external.bitrix24.lead import get_lead, update_lead
from app.modules.external.bitrix24.drive import get_file, add_file, get_public_link, create_folder_path
from app.modules.external.bitrix24.products import reload_products
from app.modules.settings import get_settings
from app.modules.cloud.services.calculation import get_cloud_products
from app.modules.offer.offer_services import add_item_v2, update_item_v2, get_one_item_v2
from app.models import OfferV2

from .quote_data import calculate_quote
from .generator import generate_cover_pdf, generate_quote_pdf, generate_datasheet_pdf, generate_summary_pdf, generate_letter_pdf, generate_contract_summary_pdf, generate_heating_pdf, generate_roof_reconstruction_pdf, generate_quote_summary_pdf
from .models.quote_history import QuoteHistory


blueprint = Blueprint("quote_calculator", __name__, template_folder='templates')


@blueprint.route("/reload_products", methods=['GET', 'POST'])
def route_reload_products():
    reload_products(force=True)
    return {"status": "success"}


@blueprint.route("/<lead_id>", methods=['GET', 'POST'])
def quote_calculator_defaults(lead_id):
    auth_info = get_auth_info()
    if auth_info is not None and auth_info["domain_raw"] == "keso.bitrix24.de":
        lead_id = int(lead_id)
        if lead_id <= 0:
            return Response(
                '{"status": "error", "error_code": "not_deal_given", "message": "deal id missing in data object"}',
                status=404,
                mimetype='application/json')
        history = QuoteHistory.query.filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
        if history is not None:
            data = history.data
            if "financing_rate" not in data["data"]:
                data["data"]["financing_rate"] = 3.79
            if "extra_options_zero" not in data["data"]:
                data["data"]["extra_options_zero"] = []
        else:
            post_data = None
            try:
                post_data = request.json
            except Exception as e:
                pass
            data = calculate_quote(lead_id, post_data)
        return Response(
            json.dumps({"status": "success", "data": data}),
            status=200,
            mimetype='application/json')
    return Response(
        '{"status": "error", "error_code": "not_authorized", "message": "user not authorized for this action"}',
        status=501,
        mimetype='application/json')


@blueprint.route("/<lead_id>/calculate", methods=['GET', 'POST'])
@api_response
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
        data = calculate_quote(lead_id, post_data)
        return Response(
            json.dumps({"status": "success", "data": data}),
            status=200,
            mimetype='application/json')
    return Response(
        '{"status": "error", "error_code": "not_authorized", "message": "user not authorized for this action"}',
        status=501,
        mimetype='application/json')


@blueprint.route("/<lead_id>", methods=['PUT'])
def quote_calculator_update(lead_id):
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

    lead = get_lead(lead_id)
    if "unique_identifier" not in lead or lead["unique_identifier"] is None or lead["unique_identifier"] != "":
        lead["unique_identifier"] = lead_id

    data = calculate_quote(lead_id, post_data)
    if "contact" in lead:
        data["contact"] = lead["contact"]
    if "upload_folder_id_roof" not in data["data"]:
        data["data"]["upload_folder_id_roof"] = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Uploads/Dachbilder")
        data["data"]["upload_link_roof"] = f"https://keso.bitrix24.de/docs/path/Auftragsordner/Vorgang {lead['unique_identifier']}/Uploads/Dachbilder"
    if "upload_folder_id_roof_extra" not in data["data"]:
        data["data"]["upload_folder_id_roof_extra"] = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Uploads/Weitere Dachbilder")
        data["data"]["upload_link_roof_extra"] = f"https://keso.bitrix24.de/docs/path/Auftragsordner/Vorgang {lead['unique_identifier']}/Uploads/Weitere Dachbilder"
    if "upload_folder_id_electric" not in data["data"]:
        data["data"]["upload_folder_id_electric"] = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Uploads/Elektrik-Bilder")
        data["data"]["upload_link_electric"] = f"https://keso.bitrix24.de/docs/path/Auftragsordner/Vorgang {lead['unique_identifier']}/Uploads/Elektrik-Bilder"
    if "upload_folder_id_heating" not in data["data"]:
        data["data"]["upload_folder_id_heating"] = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Uploads/Heizungsbilder")
        data["data"]["upload_link_heating"] = f"https://keso.bitrix24.de/docs/path/Auftragsordner/Vorgang {lead['unique_identifier']}/Uploads/Heizungsbilder"
    if "upload_folder_id_invoices" not in data["data"]:
        data["data"]["upload_folder_id_invoices"] = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Uploads/Rechnung vom bisherigem Anbieter")
        data["data"]["upload_link_invoices"] = f"https://keso.bitrix24.de/docs/path/Auftragsordner/Vorgang {lead['unique_identifier']}/Uploads/Rechnung vom bisherigem Anbieter"
    if "upload_folder_id_contract" not in data["data"]:
        data["data"]["upload_folder_id_contract"] = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Uploads/Vertragsunterlagen")
        data["data"]["upload_link_contract"] = f"https://keso.bitrix24.de/docs/path/Auftragsordner/Vorgang {lead['unique_identifier']}/Uploads/Vertragsunterlagen"
    history = QuoteHistory(
        lead_id=lead_id,
        datetime=datetime.datetime.now(),
        label="",
        data=data
    )
    db.session.add(history)
    db.session.commit()
    update_lead(lead_id, {
        "unique_identifier": str(lead_id),
        "upload_link_roof": data["data"]["upload_link_roof"],
        "upload_link_electric": data["data"]["upload_link_electric"],
        "upload_link_heating": data["data"]["upload_link_heating"],
        "upload_link_invoices": data["data"]["upload_link_invoices"],
        "upload_link_contract": data["data"]["upload_link_contract"]
    })

    return {"status": "success", "data": data}


@blueprint.route("/<lead_id>/cloud_pdfs", methods=['PUT'])
def quote_calculator_cloud_pdfs(lead_id):
    from app.modules.offer.services.pdf_generation.cloud_offer import generate_cloud_pdf
    from app.modules.offer.services.pdf_generation.feasibility_study import generate_feasibility_study_pdf

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
    lead = get_lead(lead_id)
    history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    folder_id = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Angebote/Version {history.id}")
    calculated = history.data["calculated"]
    data = history.data["data"]
    if "contact" in history.data:
        data["address"] = history.data["contact"]
    if "contact" in lead:
        data["address"] = lead["contact"]
    data["total_net"] = history.data["total_net"]
    data["tax_rate"] = history.data["tax_rate"]
    items = get_cloud_products(data={"calculated": history.data["calculated"], "data": history.data["data"]})
    offer_v2_data = {
        "reseller_id": None,
        "offer_group": "cloud-offer",
        "datetime": datetime.datetime.now(),
        "currency": "eur",
        "tax_rate": data["tax_rate"],
        "lead_id": lead_id,
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
    if "email" in lead and len(lead["email"])>0:
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
    if item.pdf is None:
        generate_cloud_pdf(item)
    history_data["calculated"]["pdf_link"] = item.pdf.longterm_public_link
    history_data["pdf_link"] = history_data["calculated"]["pdf_link"]
    history_data["pdf_cloud_config_file_id"] = item.pdf.bitrix_file_id
    if item.feasibility_study_pdf is None:
        generate_feasibility_study_pdf(item)
    history_data["calculated"]["pdf_wi_link"] = item.feasibility_study_pdf.longterm_public_link
    history_data["pdf_wi_link"] = history_data["calculated"]["pdf_wi_link"]
    history_data["pdf_wi_file_id"] = item.feasibility_study_pdf.bitrix_file_id
    history.data = history_data
    db.session.commit()
    return {"status": "success", "data": history.data}


@blueprint.route("/<lead_id>/pv_pdf", methods=['PUT'])
def quote_calculator_pv_pdf(lead_id):
    lead = get_lead(lead_id)
    history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    data = json.loads(json.dumps(history.data))

    subfolder_id = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Angebote/Version {history.id}")
    pdf_pv = generate_quote_pdf(lead_id, data)
    if pdf_pv is None:
        return Response(
            '{"status": "error", "error_code": "pdf_generation_failed", "message": "pdf generation failed: pdf_pv"}',
            status=404,
            mimetype='application/json')
    data["pdf_pv_file_id"] = add_file(folder_id=subfolder_id, data={
        "file_content": pdf_pv,
        "filename": "PV-Angebot.pdf"
    })
    if data["pdf_pv_file_id"] is None or data["pdf_pv_file_id"] <= 0:
        return Response(
            '{"status": "error", "error_code": "drive_upload_failed", "message": "bitrix drive upload failed"}',
            status=404,
            mimetype='application/json')
    history.data = data
    db.session.commit()
    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


@blueprint.route("/<lead_id>/heating_pdf", methods=['PUT'])
def quote_calculator_heating_pdf(lead_id):
    lead = get_lead(lead_id)
    history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    data = json.loads(json.dumps(history.data))

    subfolder_id = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Angebote/Version {history.id}")
    pdf_heating = generate_heating_pdf(lead_id, data)
    if pdf_heating is None:
        return Response(
            '{"status": "error", "error_code": "pdf_generation_failed", "message": "pdf generation failed: pdf_pv"}',
            status=404,
            mimetype='application/json')
    data["pdf_heating_file_id"] = add_file(folder_id=subfolder_id, data={
        "file_content": pdf_heating,
        "filename": "Heizung-Angebot.pdf"
    })
    if data["pdf_heating_file_id"] is None or data["pdf_heating_file_id"] <= 0:
        return Response(
            '{"status": "error", "error_code": "drive_upload_failed", "message": "bitrix drive upload failed"}',
            status=404,
            mimetype='application/json')
    history.data = data
    db.session.commit()
    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


@blueprint.route("/<lead_id>/roof_reconstruction_pdf", methods=['PUT'])
def quote_calculator_roof_reconstruction_pdf(lead_id):
    lead = get_lead(lead_id)
    history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    data = json.loads(json.dumps(history.data))

    subfolder_id = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Angebote/Version {history.id}")
    pdf_heating = generate_roof_reconstruction_pdf(lead_id, data)
    if pdf_heating is None:
        return Response(
            '{"status": "error", "error_code": "pdf_generation_failed", "message": "pdf generation failed: pdf_pv"}',
            status=404,
            mimetype='application/json')
    data["pdf_roof_file_id"] = add_file(folder_id=subfolder_id, data={
        "file_content": pdf_heating,
        "filename": "Dach-Angebot.pdf"
    })
    if data["pdf_roof_file_id"] is None or data["pdf_roof_file_id"] <= 0:
        return Response(
            '{"status": "error", "error_code": "drive_upload_failed", "message": "bitrix drive upload failed"}',
            status=404,
            mimetype='application/json')
    history.data = data
    db.session.commit()
    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


@blueprint.route("/<lead_id>/datasheets_pdf", methods=['PUT'])
def quote_calculator_datasheets_pdf(lead_id):
    lead = get_lead(lead_id)
    history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    data = json.loads(json.dumps(history.data))
    subfolder_id = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Angebote/Version {history.id}")

    pdf_datasheets = generate_datasheet_pdf(lead_id, data)
    if pdf_datasheets is None:
        return Response(
            '{"status": "error", "error_code": "pdf_generation_failed", "message": "pdf generation failed: pdf_datasheets"}',
            status=404,
            mimetype='application/json')
    data["pdf_datasheets_file_id"] = add_file(folder_id=subfolder_id, data={
        "file_content": pdf_datasheets,
        "filename": "Datenblaetter.pdf"
    })
    if data["pdf_datasheets_file_id"] is None or data["pdf_datasheets_file_id"] <= 0:
        return Response(
            '{"status": "error", "error_code": "drive_upload_failed", "message": "bitrix drive upload failed"}',
            status=404,
            mimetype='application/json')
    data["pdf_datasheets_link"] = get_public_link(data["pdf_datasheets_file_id"])
    history.data = data
    db.session.commit()
    update_lead(lead_id, {"pdf_datasheets_link": data["pdf_datasheets_link"]})
    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


@blueprint.route("/<lead_id>/summary_pdf", methods=['PUT', 'GET'])
def quote_calculator_summary_pdf(lead_id):
    lead = get_lead(lead_id)
    history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    data = json.loads(json.dumps(history.data))
    subfolder_id = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Angebote/Version {history.id}")

    pdf_letter = generate_cover_pdf(lead_id, data)
    if request.method == "GET":
        return Response(
            pdf_letter,
            status=200,
            mimetype='application/pdf')
    if pdf_letter is None:
        return Response(
            '{"status": "error", "error_code": "pdf_generation_failed", "message": "pdf generation failed: pdf_letter"}',
            status=404,
            mimetype='application/json')
    data["pdf_cover_file_id"] = add_file(folder_id=subfolder_id, data={
        "file_content": pdf_letter,
        "filename": "Deckblatt.pdf"
    })
    if data["pdf_cover_file_id"] is None or data["pdf_cover_file_id"] <= 0:
        return Response(
            '{"status": "error", "error_code": "drive_upload_failed", "message": "bitrix drive upload failed"}',
            status=404,
            mimetype='application/json')

    pdf_letter = generate_letter_pdf(lead_id, data)
    if pdf_letter is None:
        return Response(
            '{"status": "error", "error_code": "pdf_generation_failed", "message": "pdf generation failed: pdf_letter"}',
            status=404,
            mimetype='application/json')
    data["pdf_letter_file_id"] = add_file(folder_id=subfolder_id, data={
        "file_content": pdf_letter,
        "filename": "Anschreiben.pdf"
    })
    if data["pdf_letter_file_id"] is None or data["pdf_letter_file_id"] <= 0:
        return Response(
            '{"status": "error", "error_code": "drive_upload_failed", "message": "bitrix drive upload failed"}',
            status=404,
            mimetype='application/json')

    pdf_summary = generate_summary_pdf(lead_id, data)
    if pdf_summary is None:
        return Response(
            '{"status": "error", "error_code": "pdf_generation_failed", "message": "pdf generation failed: pdf_summary"}',
            status=404,
            mimetype='application/json')
    data["pdf_summary_file_id"] = add_file(folder_id=subfolder_id, data={
        "file_content": pdf_summary,
        "filename": "Energiemappe.pdf"
    })
    if data["pdf_summary_file_id"] is None or data["pdf_summary_file_id"] <= 0:
        return Response(
            '{"status": "error", "error_code": "drive_upload_failed", "message": "bitrix drive upload failed"}',
            status=404,
            mimetype='application/json')

    data["pdf_summary_link"] = get_public_link(data["pdf_summary_file_id"])
    history.data = data
    db.session.commit()
    update_lead(lead_id, {"pdf_summary_link": data["pdf_summary_link"]})

    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


@blueprint.route("/<lead_id>/quote_summary_pdf", methods=['PUT'])
def quote_calculator_quote_summary_pdf(lead_id):
    lead = get_lead(lead_id)
    history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    data = json.loads(json.dumps(history.data))
    subfolder_id = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Angebote/Version {history.id}")

    pdf_summary = generate_quote_summary_pdf(lead_id, data)
    if pdf_summary is None:
        return Response(
            '{"status": "error", "error_code": "pdf_generation_failed", "message": "pdf generation failed: pdf_quote_summary_file_id"}',
            status=404,
            mimetype='application/json')
    data["pdf_quote_summary_file_id"] = add_file(folder_id=subfolder_id, data={
        "file_content": pdf_summary,
        "filename": "Angebote.pdf"
    })
    if data["pdf_quote_summary_file_id"] is None or data["pdf_quote_summary_file_id"] <= 0:
        return Response(
            '{"status": "error", "error_code": "drive_upload_failed", "message": "bitrix drive upload failed"}',
            status=404,
            mimetype='application/json')

    data["pdf_quote_summary_link"] = get_public_link(data["pdf_quote_summary_file_id"])
    history.data = data
    db.session.commit()
    update_lead(lead_id, {"pdf_quote_summary_link": data["pdf_quote_summary_link"]})

    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


@blueprint.route("/<lead_id>/contract_summary_pdf", methods=['PUT'])
def quote_calculator_contract_summary_pdf(lead_id):
    lead = get_lead(lead_id)
    history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    data = json.loads(json.dumps(history.data))
    subfolder_id = create_folder_path(parent_folder_id=442678, path=f"Vorgang {lead['unique_identifier']}/Angebote/Version {history.id}")

    pdf_summary = generate_contract_summary_pdf(lead_id, data)
    if pdf_summary is None:
        return Response(
            '{"status": "error", "error_code": "pdf_generation_failed", "message": "pdf generation failed: pdf_contract_summary_file_id"}',
            status=404,
            mimetype='application/json')
    data["pdf_contract_summary_file_id"] = add_file(folder_id=subfolder_id, data={
        "file_content": pdf_summary,
        "filename": "Vertragsunterlagen.pdf"
    })
    if data["pdf_contract_summary_file_id"] is None or data["pdf_contract_summary_file_id"] <= 0:
        return Response(
            '{"status": "error", "error_code": "drive_upload_failed", "message": "bitrix drive upload failed"}',
            status=404,
            mimetype='application/json')

    data["pdf_contract_summary_link"] = get_public_link(data["pdf_contract_summary_file_id"])
    history.data = data
    db.session.commit()
    update_lead(lead_id, {"pdf_contract_summary_link": data["pdf_contract_summary_link"]})

    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


@blueprint.route("", methods=['GET', 'POST'])
def quote_calculator_index():
    config = get_settings(section="external/bitrix24")
    auth_info = get_auth_info()
    if auth_info["user"] is None:
        return "Forbidden"
    options = request.form.get("PLACEMENT_OPTIONS")
    if options is None:
        return "Keine Placement Optionen gesetzt"
    options = json.loads(options)
    if "ID" not in options:
        return "Keine ID gewählt"
    token = encode_jwt(auth_info, expire_minutes=600)
    return render_template("quote_calculator/quote_calculator.html", token=token, lead_id=options["ID"])


@blueprint.route("/install", methods=['GET', 'POST'])
def install_quote_calculator():
    env = os.getenv('ENVIRONMENT')
    return render_template("quote_calculator/install.html", domain=request.host, env=env)


@blueprint.route("/uninstall", methods=['POST'])
def uninstall_quote_calculator():
    return render_template("quote_calculator/uninstall.html", domain=request.host)
