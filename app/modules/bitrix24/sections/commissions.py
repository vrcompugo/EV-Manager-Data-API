import json
import pprint
import datetime
from dateutil.relativedelta import relativedelta
from flask import Blueprint, render_template, request, make_response, redirect

from app import db
from app.models import Reseller, Lead, Order, Commission
from app.models import ImportIdAssociation
from app.modules.order.order_services import update_item as update_order

from ..utils import get_bitrix_auth_info


def register_routes(api: Blueprint):

    @api.route("/commissions/", methods=["GET", "POST"])
    def commissions():
        auth_info = get_bitrix_auth_info(request)
        if auth_info["user"].id in [1, 12] or auth_info["user"].group_id == 8:
            now = datetime.datetime.now()
            resellers = db.session.query(Reseller).order_by(Reseller.name).filter(Reseller.active.is_(True)).all()
            for reseller in resellers:
                reseller.provided_leads_month_count = db.session.query(Lead)\
                    .filter(Lead.reseller_id == reseller.id)\
                    .filter(Lead.returned_at.is_(None))\
                    .filter(Lead.datetime >= datetime.date(now.year, now.month, 1))\
                    .filter(Lead.datetime < datetime.date(now.year, now.month + 1, 1))\
                    .count()
                reseller.won_leads_month = db.session.query(Order)\
                    .filter(Order.reseller_id == reseller.id)\
                    .filter(Order.datetime >= datetime.date(now.year, now.month, 1))\
                    .filter(Order.datetime < datetime.date(now.year, now.month + 1, 1))\
                    .count()
                reseller.win_rate = (float(reseller.won_leads_month) / float(reseller.provided_leads_month_count)) * 100.0
            return render_template("commissions/list.html", resellers=resellers, auth_info=auth_info)
        else:
            return commission_page(auth_info["user"].id)
        return "not found"

    @api.route("/commissions/<id>/store", methods=["GET", "POST"])
    def commission_store(id):
        auth_info = get_bitrix_auth_info(request)
        if auth_info["user"].id in [1, 12] or auth_info["user"].group_id == 8:
            now = datetime.datetime.now()
            year = request.args.get("year")
            if year is None or int(year) <= 0:
                year = now.year
            else:
                year = int(year)
            month = request.args.get("month")
            if month is None or int(month) <= 0:
                month = now.month
            else:
                month = int(month)
            commission = db.session.query(Commission)\
                .filter(Commission.reseller_id == id)\
                .filter(Commission.month == month)\
                .filter(Commission.year == year)\
                .first()
            if commission is None:
                commission = Commission(
                    reseller_id=id,
                    month=month,
                    year=year,
                    taxrate=19
                )
                db.session.add(commission)
            if request.form.get("extra_item") is not None:
                commission.extra_item = request.form.get("extra_item")
            if request.form.get("extra_value_net") is not None:
                commission.extra_value_net = float(request.form.get("extra_value_net").replace(".", "").replace(",", "."))
            if request.form.get("comment_internal") is not None:
                commission.comment_internal = request.form.get("comment_internal")
            if request.form.get("comment_external") is not None:
                commission.comment_external = request.form.get("comment_external")
            if request.form.get("comment_external") is not None:
                commission.comment_external = request.form.get("comment_external")
            if request.form.getlist("provision_checked_net[]") is not None:
                for provision_checked_net in request.form.getlist("provision_checked_net[]"):
                    provision_checked_net = json.loads(provision_checked_net)
                    if provision_checked_net["value"] != "":
                        order = db.session.query(Order)\
                            .filter(Order.id == int(provision_checked_net["id"]))\
                            .first()
                        order.commissions[int(provision_checked_net["index"])]["provision_checked_net"] = float(provision_checked_net["value"])
                        tmp = json.dumps(order.commissions)
                        update_order(order.id, {"commissions": None})
                        update_order(order.id, {"commissions": json.loads(tmp)})
                        print(json.loads(tmp))
            if request.args.get("checked") is not None:
                order = db.session.query(Order)\
                    .filter(Order.id == int(request.args.get("checked")))\
                    .first()
                if order is not None:
                    order.is_checked = not order.is_checked
            if request.args.get("booked") is not None:
                order = db.session.query(Order)\
                    .filter(Order.id == int(request.args.get("booked")))\
                    .first()
                if order is not None:
                    order.is_paid = not order.is_paid
            db.session.commit()

        return commission_page(id)

    @api.route("/commissions/<id>", methods=["GET", "POST"])
    def commission_page(id):
        auth_info = get_bitrix_auth_info(request)
        if auth_info["user"].id in [1, 12, id]:
            can_edit = False
            if auth_info["user"].id in [1, 12] or auth_info["user"].group_id == 8:
                can_edit = True
            reseller = db.session.query(Reseller).get(id)
            now = datetime.datetime.now()
            year = request.args.get("year")
            if year is None or int(year) <= 0:
                year = now.year
            else:
                year = int(year)
            month = request.args.get("month")
            if month is None or int(month) <= 0:
                month = now.month
            else:
                month = int(month)
            day_of_year = float(now.strftime("%-j"))
            base_date = datetime.date(year, month, 1)
            commission = db.session.query(Commission)\
                .filter(Commission.reseller_id == id)\
                .filter(Commission.month == month)\
                .filter(Commission.year == year)\
                .first()
            if commission is not None:
                if commission.extra_value_net is None:
                    commission.extra_value_net = 0
                commission.extra_value_net = float(round(commission.extra_value_net, 2))
            provided_leads_year_count = db.session.query(Lead)\
                .filter(Lead.reseller_id == reseller.id)\
                .filter(Lead.returned_at.is_(None))\
                .filter(Lead.datetime >= datetime.date(base_date.year, 1, 1))\
                .filter(Lead.datetime <= datetime.date(base_date.year, 12, 31))\
                .count()
            provided_leads_month_count = db.session.query(Lead)\
                .filter(Lead.reseller_id == reseller.id)\
                .filter(Lead.returned_at.is_(None))\
                .filter(Lead.datetime >= datetime.date(base_date.year, base_date.month, 1))\
                .filter(Lead.datetime < datetime.date(base_date.year, base_date.month + 1, 1))\
                .count()
            won_leads_year_count = db.session.query(Order)\
                .filter(Order.reseller_id == reseller.id)\
                .filter(Order.datetime >= datetime.date(base_date.year, 1, 1))\
                .filter(Order.datetime <= datetime.date(base_date.year, 12, 31))\
                .count()
            won_leads_month_raw = db.session.query(Order, ImportIdAssociation)\
                .outerjoin(ImportIdAssociation, ImportIdAssociation.local_id == Order.id)\
                .filter(ImportIdAssociation.model == "Order")\
                .filter(ImportIdAssociation.source == "bitrix24")\
                .filter(Order.reseller_id == reseller.id)\
                .filter(Order.datetime >= datetime.date(base_date.year, base_date.month, 1))\
                .filter(Order.datetime < datetime.date(base_date.year, base_date.month + 1, 1))\
                .order_by(Order.datetime.asc())\
                .all()

            time_select = datetime.date(2020, 1, 1)
            time_select_options = []
            while time_select < datetime.date(now.year, now.month, 1):
                time_select_options.append({
                    "value": f"year={time_select.year}&month={time_select.month}",
                    "label": f"{time_select.month} {time_select.year}",
                    "selected": (time_select.month == base_date.month and time_select.year == base_date.year)
                })
                time_select = time_select + relativedelta(months=+1)
            time_select_options.reverse()
            won_leads_month = []
            for lead in won_leads_month_raw:
                if lead[1] is not None:
                    lead[0].remote_id = lead[1].remote_id
                won_leads_month.append(lead[0])
            return render_template(
                "commissions/report.html",
                day_of_year=day_of_year,
                reseller=reseller,
                auth_info=auth_info,
                provided_leads_year_count=provided_leads_year_count,
                provided_leads_month_count=provided_leads_month_count,
                won_leads_year_count=won_leads_year_count,
                won_leads_month_count=len(won_leads_month),
                won_leads_month=won_leads_month,
                can_edit=can_edit,
                time_select_options=time_select_options,
                commission=commission
            )
        return "not found"

    @api.route("/commissions/install/", methods=["POST"])
    def commissions_installer():
        return render_template("commissions/install.html")
