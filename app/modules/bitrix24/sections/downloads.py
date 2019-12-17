from flask import Blueprint, render_template, request, make_response
import json
import pprint
import datetime

from app.models import Lead, OfferV2, LeadComment, S3File

from ..utils import get_bitrix_auth_info


def register_routes(api: Blueprint):

    @api.route("/downloads/", methods=["GET", "POST"])
    def downloads():

        if request.form.get("PLACEMENT") == "CRM_LEAD_DETAIL_TAB":
            lead_id = json.loads(request.form.get("PLACEMENT_OPTIONS"))["ID"]
            lead = Lead.query.filter(Lead.id == lead_id).first()
            if lead is None:
                return "Lead not found2"
            return render_template("downloads/lead_downloads.html", lead=lead)
        return "No Placement"

    @api.route("/downloads/reload/", methods=["GET"])
    def reload():
        from app.modules.importer.sources.bitrix24._connector import post, get
        lead_id = request.args.get("lead_id")
        lead = Lead.query.filter(Lead.id == lead_id).first()
        if lead is None:
            return "Lead not found2"

        response = post("crm.quote.list", post_data={
            "filter[LEAD_ID]": 400,
            "order[id]": "desc"
        })
        offers_data = []
        for offer in response["result"]:
            date_time_obj = datetime.datetime.strptime(offer["DATE_CREATE"], '%Y-%m-%dT%H:%M:%S%z')
            offer_data = {
                "id": offer["ID"],
                "datetime": date_time_obj.strftime("%d.%m.%Y"),
                "number": offer["QUOTE_NUMBER"],
                "download_link": "#"
            }
            response = post("crm.documentgenerator.document.list", post_data={
                "filter[entityId]": offer["ID"]
            })
            if "result" in response and "documents" in response["result"] and len(response["result"]["documents"])>0:
                offer_data["download_link"] = response["result"]["documents"][0]["pdfUrl"]

            offers_data.append(offer_data)

        lead_comment = LeadComment.query.filter(LeadComment.lead_id == lead.id).order_by(LeadComment.datetime.desc()).first()
        if lead_comment is not None:
            for attachment in lead_comment.attachments:
                s3_file = S3File.query.get(attachment["id"])
                if s3_file is None:
                    attachment["public_link"] = "#"
                else:
                    attachment["public_link"] = s3_file.public_link()
        return render_template("downloads/lead_downloads_list.html", offers=offers_data, lead_comment=lead_comment)

    @api.route("/downloads/install/", methods=[ "POST"])
    def installer():
        return render_template("downloads/install.html")
