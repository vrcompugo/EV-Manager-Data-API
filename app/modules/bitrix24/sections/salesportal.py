from flask import Blueprint, render_template, request, make_response
import json
import pprint
import datetime

from app.models import Lead, OfferV2, LeadComment, S3File

from ..utils import get_bitrix_auth_info


def register_routes(api: Blueprint):

    @api.route("/salesportal/", methods=["GET", "POST"])
    def salesportal():
        from app.modules.importer.sources.bitrix24._association import find_association
        from app.modules.importer.sources.bitrix24.lead import run_import

        if request.form.get("PLACEMENT") == "CRM_LEAD_DETAIL_TAB":
            auth_info = get_bitrix_auth_info(request)
            lead_id = json.loads(request.form.get("PLACEMENT_OPTIONS"))["ID"]
            lead_link = find_association("Lead", remote_id=lead_id)
            if lead_link is None:
                run_import(remote_id=lead_id)
                lead_link = find_association("Lead", remote_id=lead_id)
            if lead_link is None:
                return "Lead not found"
            lead = Lead.query.filter(Lead.id == lead_link.local_id).first()
            if lead is None:
                return "Lead not found2"
            return render_template("salesportal/iframe.html", lead=lead, auth_info=auth_info)
        return "No Placement"

    @api.route("/salesportal/install/", methods=["POST"])
    def salesportal_installer():
        return render_template("salesportal/install.html")
