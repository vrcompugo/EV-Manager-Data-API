import jwt
import json
import datetime
from flask import Blueprint, render_template, request, make_response

from app import db
from app.config import key
from app.modules.auth.auth_services import get_logged_in_user
from app.modules.order.order_services import generate_contract_number
from app.models import Order

from ..utils import get_bitrix_auth_info


def register_routes(api: Blueprint):

    @api.route("/cloud_data/", methods=["GET", "POST"])
    def cloud_data_iframe():
        from app.modules.importer.sources.bitrix24._association import find_association
        from app.modules.importer.sources.bitrix24.order import run_import as order_import

        auth_info = get_bitrix_auth_info(request)
        if "user2" not in auth_info:
            return "Forbidden"
        encoded_jwt = jwt.encode(
            payload={
                'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30),
                'iat': datetime.datetime.utcnow(),
                'sub': auth_info["user2"].id
            },
            key=key,
            algorithm='HS256')
        if request.form.get("PLACEMENT") != "CRM_DEAL_DETAIL_TAB":
            return "Kein Placement"
        order_id = json.loads(request.form.get("PLACEMENT_OPTIONS"))["ID"]
        order = order_import(remote_id=order_id)
        if order is None:
            return "Import fehlgeschlagen"
        if order.category != "Cloud Verträge":
            return "Nur Cloud Verträge"
        order_link = find_association("Order", remote_id=order_id)
        if order_link is None:
            return "Order not found"
        return render_template("cloud_data/iframe.html", encoded_jwt=encoded_jwt.decode(), order_id=order_link.local_id)

    @api.route("/cloud_data/generate_contract_number/<order_id>", methods=["POST"])
    def cloud_data_generate_contract_number(order_id):
        from app.modules.importer.sources.bitrix24.order import run_export_fields
        from app.modules.importer.sources.bitrix24.order import run_import as order_import
        auth_info = get_logged_in_user()
        order_import(local_id=order_id)
        order = db.session.query(Order).get(order_id)
        db.session.refresh(order)
        contract_number = generate_contract_number(order)
        if contract_number is not None:
            order.contract_number = contract_number
            db.session.commit()
            result = run_export_fields(local_id=order.id, fields=["contract_number"])
            print(contract_number, result)

        return '{"status": "success"}'

    @api.route("/cloud_data/sherpa_export/<order_id>/<token>", methods=["GET"])
    def cloud_data_sherpa_export(order_id, token):
        from app.modules.importer.sources.bitrix24.order import run_import as order_import
        from app.modules.order.sherpa import generate_sherpa_file
        auth_info = get_logged_in_user(auth_token=token)
        order_import(local_id=order_id)
        order = db.session.query(Order).get(order_id)
        db.session.refresh(order)
        sherpa_file = generate_sherpa_file(order)
        if sherpa_file is not None:
            response = make_response(sherpa_file)
            response.headers['Content-Type'] = 'application/excel'
            response.headers['Content-Disposition'] = f'filename={order.contract_number}.xlsx'
            return response

        return '{"status": "success"}'

    @api.route("/cloud_data/install/", methods=["POST"])
    def cloud_data_installer():
        return render_template("cloud_data/install.html")
