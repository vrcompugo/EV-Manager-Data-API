from flask_restplus import Resource
from sqlalchemy import and_, not_
import datetime

from app.decorators import token_required, api_response
from app.exceptions import ApiException
from app.models import Lead

from .reseller_routes import api
from ..models.reseller import Reseller


@api.route('/<id>/statistics/leads')
class Items(Resource):
    @api_response
    @api.doc(params={})
    @token_required("show_reseller")
    def get(self, id):
        if id is None:
            raise ApiException("no id given", "No ID given", 404)
        reseller = Reseller.query.filter(Reseller.id == id).first()
        if reseller is None:
            reseller = Reseller.query.filter(Reseller.number == id).first()
            if reseller is None:
                raise ApiException("item_doesnt_exist", "Item doesn't exist.", 404)
        now = datetime.datetime.now()
        leads_base = Lead.query\
            .filter(Lead.reseller_id == reseller.id)

        data = {
            "id": reseller.id,
            "number": reseller.number,
            "email": reseller.email,
            "total_leads": leads_base.count(),
            "total_won_leads": leads_base.filter(Lead.status == "won").count(),
            "total_lost_leads": leads_base.filter(Lead.status == "lost").count(),
            "months": []
        }
        data["total_pending_leads"] = data["total_leads"] - data["total_won_leads"] - data["total_lost_leads"]
        data["total_win_rate"] = 0
        if data["total_leads"] > 0:
            data["total_win_rate"] = round((data["total_won_leads"] / data["total_leads"]) * 100, 2)
        for i in range(0,4):
            month = leads_base\
                .filter(and_(
                        Lead.datetime >= datetime.date(now.year, now.month - i, 1),
                        Lead.datetime < datetime.date(now.year, now.month - i + 1, 1)
                    )
                )
            data["months"].append({})
            data["months"][i]["total_leads"] = month.count()
            data["months"][i]["total_won_leads"] = month.filter(Lead.status == "won").count()
            data["months"][i]["total_lost_leads"] = month.filter(Lead.status == "lost").count()
            data["months"][i]["total_pending_leads"] = data["months"][i]["total_leads"] \
                                                       - data["months"][i]["total_won_leads"] \
                                                       - data["months"][i]["total_lost_leads"]
            data["months"][i]["total_win_rate"] = 0
            if data["months"][i]["total_leads"] > 0:
                data["months"][i]["total_win_rate"] = round((data["months"][i]["total_won_leads"] / data["months"][i]["total_leads"]) * 100, 2)
        return {"status":"success",
                "data": data}

