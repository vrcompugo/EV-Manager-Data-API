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
        if auth_info["user"] is None:
            return "not authenticated"
        if auth_info["user"].id in [1, 12, 47]:
            resellers = db.session.query(Reseller).filter(Reseller.active.is_(True)).order_by(Reseller.name).all()
            return render_template("resellers/list.html", resellers=resellers, auth_info=auth_info)
        else:
            return reseller(auth_info["user"].id)
        return "not found"

    @api.route("/resellers/<id>", methods=["GET", "POST"])
    def reseller(id):
        auth_info = get_bitrix_auth_info(request)
        if auth_info["user"].id in [1, 12, 47]:
            reseller = db.session.query(Reseller).get(id)
            data = {}
            if "sales_center" in request.form:
                data["sales_center"] = request.form.get("sales_center")
            if "ziplist" in request.form:
                data["ziplist"] = request.form.get("ziplist").split("\n")
                data["ziplist"] = [zipcode.replace("\r", "") for zipcode in data["ziplist"]]
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
                reseller = update_item(reseller.id, data)
            if reseller.ziplist is None:
                reseller.ziplist = ""
            else:
                reseller.ziplist = "\n".join(reseller.ziplist)
            return render_template(
                "resellers/reseller.html",
                reseller=reseller,
                auth_info=auth_info
            )
        return "not found"

    @api.route("/resellers/install/", methods=["POST"])
    def resellers_installer():
        return render_template("resellers/install.html")
