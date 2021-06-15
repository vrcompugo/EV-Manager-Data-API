import json
import os
from flask import Blueprint, request, render_template

from app.modules.auth import get_auth_info
from app.modules.auth.jwt_parser import encode_jwt
from app.modules.external.fakturia.deal import get_contract_data_by_deal


blueprint = Blueprint("fakturia", __name__, template_folder='templates')


@blueprint.route("/<deal_id>", methods=['GET'])
def get_deal_data(deal_id):
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return {"status": "failed", "data": {}, "message": "auth failed"}
    data = get_contract_data_by_deal(deal_id)
    if data is not None:
        return {"status": "success", "data": data}
    return {"status": "failed", "data": {}, "message": "history not found"}


@blueprint.route("", methods=['GET', 'POST'])
def fakturia_index():
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
    return render_template("fakturia/fakturia.html", token=token, deal_id=options["ID"])


@blueprint.route("/install", methods=['GET', 'POST'])
def install_fakturia():
    env = os.getenv('ENVIRONMENT')
    return render_template("fakturia/install.html", domain=request.host, env=env)


@blueprint.route("/uninstall", methods=['POST'])
def uninstall_fakturia():
    return render_template("fakturia/uninstall.html", domain=request.host)
