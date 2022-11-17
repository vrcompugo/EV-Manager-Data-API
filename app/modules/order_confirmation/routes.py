import requests
import json
import os
import datetime
from flask import Blueprint, request, render_template, redirect, make_response, Response

from app import db
from app.decorators import api_response
from app.modules.auth import get_auth_info
from app.modules.auth.jwt_parser import decode_jwt, encode_jwt
from app.modules.external.bitrix24.quote import get_quote, get_quote_products, update_quote
from app.modules.external.bitrix24.drive import get_file, add_file, get_public_link, create_folder_path
from app.modules.external.bitrix24.contact import add_contact
from app.modules.settings import get_settings
from app.models import OfferV2, QuoteHistory

from .generator import generate_order_confirmation_pdf


blueprint = Blueprint("order_confirmation", __name__, template_folder='templates')


@blueprint.route("/<quote_id>/PDF", methods=['GET', 'POST'])
def order_confirmation_pdf(quote_id):
    auth_info = get_auth_info()
    if auth_info is not None and auth_info["domain_raw"] == "keso.bitrix24.de":
        quote_id = int(quote_id)
        if quote_id <= 0:
            return Response(
                '{"status": "error", "error_code": "not_deal_given", "message": "quote id missing in data object"}',
                status=404,
                mimetype='application/json')
        post_data = request.json
        quote = get_quote(quote_id)
        if quote.get("pdf_link", None) is not None and quote.get("pdf_link", None) != "":
            print("saves")
            return Response(
                json.dumps({"status": "success", "data": {
                    "pdf_link": quote.get("pdf_link")
                }}),
                status=200,
                mimetype='application/json')
        else:
            return order_confirmation_generate(quote_id)
    return Response(
        '{"status": "error", "error_code": "not_authorized", "message": "user not authorized for this action"}',
        status=501,
        mimetype='application/json')


@blueprint.route("/<quote_id>/generate", methods=['GET', 'POST'])
def order_confirmation_generate(quote_id):
    auth_info = get_auth_info()
    if auth_info is not None and auth_info["domain_raw"] == "keso.bitrix24.de":
        quote_id = int(quote_id)
        if quote_id <= 0:
            return Response(
                '{"status": "error", "error_code": "not_deal_given", "message": "quote id missing in data object"}',
                status=404,
                mimetype='application/json')
        post_data = request.json
        quote = get_quote(quote_id)
        quote["products"] = get_quote_products(quote_id)
        data = {
            "data": post_data,
            "quote": quote,
        }
        if quote.get("expected_construction_week", None) is None or quote.get("expected_construction_week", None) == "":
            expected_construction_datetime = datetime.datetime.now() + datetime.timedelta(weeks=18)
            quote["expected_construction_week"] = expected_construction_datetime.strftime("%W/%Y")
        subfolder_id = create_folder_path(parent_folder_id=442678, path=f"Vorgang {quote['unique_identifier']}/Angebote/Version {quote['history_id']}")
        pdf = generate_order_confirmation_pdf(quote_id, quote)
        if pdf is None:
            return Response(
                '{"status": "error", "error_code": "pdf_generation_failed", "message": "pdf generation failed: order_confirmation"}',
                status=404,
                mimetype='application/json')
        data["pdf_id"] = add_file(folder_id=subfolder_id, data={
            "file_content": pdf,
            "filename": "Auftragsbestätigung.pdf"
        })
        if data["pdf_id"] is None or data["pdf_id"] <= 0:
            return Response(
                '{"status": "error", "error_code": "drive_upload_failed", "message": "bitrix drive upload failed"}',
                status=404,
                mimetype='application/json')
        data["pdf_link"] = get_public_link(data["pdf_id"], expire_minutes=365*24*60)
        update_quote(quote_id, {
            "pdf_link": data["pdf_link"],
            "expected_construction_week": quote["expected_construction_week"]
        })
        return Response(
            json.dumps({"status": "success", "data": data}),
            status=200,
            mimetype='application/json')
    return Response(
        '{"status": "error", "error_code": "not_authorized", "message": "user not authorized for this action"}',
        status=501,
        mimetype='application/json')


@blueprint.route("", methods=['GET', 'POST'])
def order_confirmation_index():
    config = get_settings(section="external/bitrix24")
    auth_info = get_auth_info()
    if auth_info["user"] is None:
        return "Forbidden"
    options = request.form.get("PLACEMENT_OPTIONS")
    if options is None:
        return "Keine Placement Optionen gesetzt"
    options = json.loads(options)
    if "ENTITY_ID" not in options:
        return "Keine ID gewählt"
    token = encode_jwt(auth_info, expire_minutes=600)
    return render_template("order_confirmation/order_confirmation.html", token=token, quote_id=options["ENTITY_ID"])


@blueprint.route("/install", methods=['GET', 'POST'])
def order_confirmation_install():
    env = os.getenv('ENVIRONMENT')
    return render_template("order_confirmation/install.html", domain=request.host, env=env)


@blueprint.route("/uninstall", methods=['POST'])
def order_confirmation_uninstall():
    return render_template("order_confirmation/uninstall.html", domain=request.host)
