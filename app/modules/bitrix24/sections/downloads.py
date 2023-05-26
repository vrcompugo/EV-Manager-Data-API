from flask import Blueprint, render_template, request, make_response
import json
import pprint
import datetime

from app.models import Lead, OfferV2, LeadComment, S3File, Order, QuoteHistory
from app.modules.external.bitrix24.deal import get_deal

from ..utils import get_bitrix_auth_info


def register_routes(api: Blueprint):

    @api.route("/downloads/", methods=["GET", "POST"])
    def downloads():

        lead_id = None
        if request.form.get("PLACEMENT") == "CRM_LEAD_DETAIL_TAB":
            lead_id = json.loads(request.form.get("PLACEMENT_OPTIONS"))["ID"]
        if request.form.get("PLACEMENT") == "CRM_DEAL_DETAIL_TAB":
            order_id = json.loads(request.form.get("PLACEMENT_OPTIONS"))["ID"]
            deal_data = get_deal(order_id)
            if deal_data.get("unique_identifier") not in [None, "", "0"]:
                lead_id = deal_data.get("unique_identifier")
        if lead_id is not None:
            return render_template("downloads/lead_downloads.html", lead_id=lead_id)
        return "No Placement"

    @api.route("/downloads/reload/", methods=["GET"])
    def reload():
        return "error1", 500
        from app.modules.importer.sources.bitrix24._connector import post
        from app.modules.importer.sources.bitrix24._association import find_association

        lead_id = request.args.get("lead_id")
        lead = Lead.query.filter(Lead.id == lead_id).first()
        lead_link = find_association("Lead", local_id=lead_id)
        if lead is None or lead_link is None:
            return "Lead not found"

        offers = OfferV2.query.filter(OfferV2.lead_id == lead.id).order_by(OfferV2.datetime.desc()).all()

        lead_comments = LeadComment.query.filter(LeadComment.lead_id == lead.id).order_by(LeadComment.datetime.desc()).all()
        for lead_comment in lead_comments:
            if lead_comment.attachments is not None:
                for attachment in lead_comment.attachments:
                    s3_file = S3File.query.get(attachment["id"])
                    if s3_file is None:
                        attachment["public_link"] = "#"
                    else:
                        attachment["public_link"] = s3_file.public_link
        histories = QuoteHistory.query.filter(QuoteHistory.lead_id == lead_link.remote_id).order_by(QuoteHistory.datetime.desc()).all()
        return render_template("downloads/lead_downloads_list.html", offers=offers, lead_comments=lead_comments, histories=histories)


    @api.route("/downloads/reload2/", methods=["GET"])
    def reload2():
        return "error1", 500
        lead_id = request.args.get("lead_id")
        histories = QuoteHistory.query.filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).all()
        return render_template("downloads/lead_downloads2_list.html", histories=histories)


    @api.route("/downloads/install/", methods=["POST"])
    def installer():
        return render_template("downloads/install.html")
