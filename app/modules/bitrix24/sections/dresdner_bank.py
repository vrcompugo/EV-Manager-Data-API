from flask import Blueprint, render_template, request, make_response
import json
import pprint
import datetime

from ..utils import get_bitrix_auth_info


def register_routes(api: Blueprint):

    @api.route("/dresdner/", methods=["GET", "POST"])
    def dresdner():
        if request.form.get("PLACEMENT") == "CRM_LEAD_DETAIL_TAB":
            return render_template("dresdner_bank/iframe.html")
        return "No Placement"

    @api.route("/dresdner/install/", methods=["POST"])
    def dresdner_installer():
        return render_template("dresdner_bank/install.html")
