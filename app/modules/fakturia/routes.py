import json
import os
from flask import Blueprint, request, render_template, make_response

from app import db
from app.exceptions import ApiException
from app.decorators import api_response
from app.modules.external.bitrix24.deal import update_deal
from app.modules.auth import get_auth_info
from app.modules.auth.jwt_parser import encode_jwt
from app.modules.external.fakturia.deal import export_deal, get_contract_data_by_deal, assign_subdeal_to_item, add_item_list, delete_item_list, update_item_list_item


blueprint = Blueprint("fakturia", __name__, template_folder='templates')


@blueprint.route("/<deal_id>", methods=['GET'])
@api_response
def get_deal_data(deal_id):
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return {"status": "failed", "data": {}, "message": "auth failed"}
    data = get_contract_data_by_deal(deal_id)
    if data is not None:
        print(data)
        return {"status": "success", "data": data}
    return {"status": "failed", "data": {}, "message": "history not found"}


@blueprint.route("/<deal_id>/export", methods=['POST'])
@api_response
def export_deal_route(deal_id):
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return {"status": "failed", "data": {}, "message": "auth failed"}
    data = export_deal(deal_id)
    if data is not None:
        return {"status": "success", "data": data}
    return {"status": "failed", "data": {}, "message": "history not found"}


@blueprint.route("/<deal_id>/sherpa_export", methods=['GET'])
@api_response
def export_deal_sherpa_route(deal_id):
    from app.modules.importer.sources.bitrix24.order import run_import as order_import
    from app.modules.order.sherpa import generate_sherpa_file
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return {"status": "failed", "data": {}, "message": "auth failed"}
    order = order_import(remote_id=deal_id)
    if order is None:
        return {"status": "failed", "data": {}, "message": "import failed"}
    sherpa_file = generate_sherpa_file(order)
    if sherpa_file is not None:
        response = make_response(sherpa_file)
        response.headers['Content-Type'] = 'application/excel'
        response.headers['Content-Disposition'] = f'filename={order.contract_number}.xlsx'
        return response
    return {"status": "failed", "data": {}, "message": "history not found"}


@blueprint.route("/<deal_id>/create_contract_number", methods=['POST'])
@api_response
def create_contract_number_route(deal_id):
    from app.modules.importer.sources.bitrix24.order import run_export_fields
    from app.modules.importer.sources.bitrix24.order import run_import as order_import
    from app.modules.order.order_services import generate_contract_number

    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return {"status": "failed", "data": {}, "message": "auth failed"}
    order = order_import(remote_id=deal_id)
    if order is None:
        return {"status": "failed", "data": {}, "message": "import failed"}
    contract_number = generate_contract_number(order)
    if contract_number is not None:
        order.contract_number = contract_number
        db.session.commit()
        run_export_fields(local_id=order.id, fields=["contract_number"])
        data = get_contract_data_by_deal(deal_id)
        return {"status": "success", "data": data}
    return {"status": "failed", "data": {}, "message": "history not found"}


@blueprint.route("/<deal_id>/to_master", methods=['POST'])
@api_response
def set_master_deal(deal_id):
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return {"status": "failed", "data": {}, "message": "auth failed"}
    update_deal(deal_id, {
        "is_cloud_master_deal": 1
    })
    data = get_contract_data_by_deal(deal_id)
    if data is not None:
        return {"status": "success", "data": data}
    return {"status": "failed", "data": {}, "message": "history not found"}


@blueprint.route("/<deal_id>/item", methods=['POST'])
@api_response
def add_item_list_route(deal_id):
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return {"status": "failed", "data": {}, "message": "auth failed"}
    data = request.json
    data = add_item_list(deal_id, data)
    if data is not None:
        return {"status": "success", "data": data}
    return {"status": "failed", "data": {}, "message": "history not found"}


@blueprint.route("/<deal_id>/item/<list_index>/<index>", methods=['PUT'])
@api_response
def store_item_list_route(deal_id, list_index, index):
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return {"status": "failed", "data": {}, "message": "auth failed"}
    data = request.json
    data = update_item_list_item(deal_id, list_index, index, data)
    if data is not None:
        return {"status": "success", "data": data}
    return {"status": "failed", "data": {}, "message": "history not found"}


@blueprint.route("/<deal_id>/item/<list_index>", methods=['DELETE'])
@api_response
def delete_item_list_route(deal_id, list_index):
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return {"status": "failed", "data": {}, "message": "auth failed"}
    data = request.json
    data = delete_item_list(deal_id, list_index)
    if data is not None:
        return {"status": "success", "data": data}
    return {"status": "failed", "data": {}, "message": "history not found"}


@blueprint.route("/<deal_id>/item/<list_index>/<item_index>/deal", methods=['POST'])
@api_response
def assign_subdeal_item(deal_id, list_index, item_index):
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return {"status": "failed", "data": {}, "message": "auth failed"}
    sub_deal_id = request.json.get("sub_deal_id")
    if sub_deal_id in [None, "", "0", 0]:
        return {"status": "failed", "data": {}, "message": "no subdeal"}
    assign_subdeal_to_item(deal_id, list_index, item_index, sub_deal_id)
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
