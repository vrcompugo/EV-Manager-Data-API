import json
import pprint
import datetime
from flask import Blueprint, render_template, request, make_response, redirect

from app import db
from app.models import Reseller, Lead, Order
from app.modules.reseller.services.reseller_services import update_item

from ..utils import get_bitrix_auth_info


def register_routes(api: Blueprint):

    @api.route("/resellers/", methods=["GET", "POST"])
    def resellers():
        auth_info = get_bitrix_auth_info(request)
        if auth_info["user"].id == 1 or auth_info["user"].id == 12:
            resellers = db.session.query(Reseller).order_by(Reseller.name).all()
            return render_template("resellers/list.html", resellers=resellers, auth_info=auth_info)
        else:
            return commission(auth_info["user"].id)
        return "not found"

    @api.route("/resellers/<id>", methods=["GET", "POST"])
    def reseller(id):
        auth_info = get_bitrix_auth_info(request)
        if auth_info["user"].id in [1, 12]:
            reseller = db.session.query(Reseller).get(id)
            data = {}
            if "sales_center" in request.form:
                data["sales_center"] = request.form.get("sales_center")
            if "sales_range" in request.form:
                data["sales_range"] = int(request.form.get("sales_range"))
            if "lead_balance" in request.form:
                data["lead_balance"] = int(request.form.get("lead_balance")) * -1
            if "leads_per_month" in request.form:
                data["leads_per_month"] = int(request.form.get("leads_per_month"))
            if "min_commission" in request.form and request.form.get("min_commission") != "":
                data["min_commission"] = float(request.form.get("min_commission"))
            if "lead_year_target" in request.form:
                data["lead_year_target"] = int(request.form.get("lead_year_target"))
            if len(data) > 0:
                update_item(reseller.id, data)
            return render_template(
                "resellers/reseller.html",
                reseller=reseller,
                auth_info=auth_info
            )
        return "not found"

    @api.route("/resellers/install/", methods=["POST"])
    def resellers_installer():
        return render_template("resellers/install.html")
