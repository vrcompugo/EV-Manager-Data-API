from flask import Blueprint, render_template, request, make_response
import json
import pprint
import datetime

from app.models import Lead, OfferV2, LeadComment, S3File, Order

from ..utils import get_bitrix_auth_info


def register_routes(api: Blueprint):

    @api.route("/salesportal/", methods=["GET", "POST"])
    def salesportal():
        from app.modules.importer.sources.bitrix24._association import find_association
        from app.modules.importer.sources.bitrix24.lead import run_import
        from app.modules.importer.sources.bitrix24.order import run_import as order_import

        auth_info = get_bitrix_auth_info(request)
        lead = None
        if request.form.get("PLACEMENT") == "CRM_LEAD_DETAIL_TAB":
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
        if request.form.get("PLACEMENT") == "CRM_DEAL_DETAIL_TAB":
            order_id = json.loads(request.form.get("PLACEMENT_OPTIONS"))["ID"]
            order_link = find_association("Order", remote_id=order_id)
            if order_link is None:
                order_import(remote_id=order_id)
                order_link = find_association("Lead", remote_id=lead_id)
            if order_link is None:
                return "Order not found"
            order = Order.query.filter(Order.id == order_link.local_id).first()
            lead = Lead.query.filter(Lead.customer_id == order.customer_id).first()
            if lead is None:
                return "Order Lead not found"
        if lead is not None:
            return render_template("salesportal/iframe.html", lead=lead, auth_info=auth_info)
        return "No Placement"

    @api.route("/salesportal/install/", methods=["POST"])
    def salesportal_installer():
        return render_template("salesportal/install.html")
