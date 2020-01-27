import json
import pprint
import datetime
from flask import Blueprint, render_template, request, make_response, redirect

from app import db
from app.models import Reseller, Lead, Order

from ..utils import get_bitrix_auth_info


def register_routes(api: Blueprint):

    @api.route("/commissions/", methods=["GET", "POST"])
    def commissions():
        auth_info = get_bitrix_auth_info(request)
        if auth_info["user"].id == 1 or auth_info["user"].id == 12:
            resellers = db.session.query(Reseller).order_by(Reseller.name).all()
            return render_template("commissions/list.html", resellers=resellers, auth_info=auth_info)
        else:
            return commission(auth_info["user"].id)
        return "not found"

    @api.route("/commissions/<id>", methods=["GET", "POST"])
    def commission(id):
        auth_info = get_bitrix_auth_info(request)
        if auth_info["user"].id in [1, 12, id]:
            reseller = db.session.query(Reseller).get(id)
            now = datetime.datetime.now()
            day_of_year = float(now.strftime("%-j"))
            base_date = datetime.date(2020, 1, 2)
            provided_leads_year_count = db.session.query(Lead)\
                .filter(Lead.reseller_id == reseller.id)\
                .filter(Lead.returned_at.is_(None))\
                .filter(Lead.counted_at >= datetime.date(base_date.year, 1, 1))\
                .filter(Lead.counted_at <= datetime.date(base_date.year, 12, 31))\
                .count()
            provided_leads_month_count = db.session.query(Lead)\
                .filter(Lead.reseller_id == reseller.id)\
                .filter(Lead.returned_at.is_(None))\
                .filter(Lead.counted_at >= datetime.date(base_date.year, base_date.month, 1))\
                .filter(Lead.counted_at < datetime.date(base_date.year, base_date.month + 1, 1))\
                .count()
            won_leads_year_count = db.session.query(Order)\
                .filter(Lead.reseller_id == reseller.id)\
                .filter(Order.datetime >= datetime.date(base_date.year, 1, 1))\
                .filter(Order.datetime <= datetime.date(base_date.year, 12, 31))\
                .count()
            won_leads_month = db.session.query(Order)\
                .filter(Order.reseller_id == reseller.id)\
                .filter(Order.datetime >= datetime.date(base_date.year, base_date.month, 1))\
                .filter(Order.datetime < datetime.date(base_date.year, base_date.month + 1, 1))\
                .all()
            return render_template(
                "commissions/report.html",
                day_of_year=day_of_year,
                reseller=reseller,
                auth_info=auth_info,
                provided_leads_year_count=provided_leads_year_count,
                provided_leads_month_count=provided_leads_month_count,
                won_leads_year_count=won_leads_year_count,
                won_leads_month_count=len(won_leads_month),
                won_leads_month=won_leads_month
            )
        return "not found"

    @api.route("/commissions/install/", methods=["POST"])
    def commissions_installer():
        return render_template("commissions/install.html")
