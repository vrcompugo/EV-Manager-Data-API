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
            raise ApiException("item_doesnt_exist", "Item doesn't exist.", 404)
        now = datetime.datetime.now()
        leads_base = Lead.query\
            .filter(Lead.reseller_id == reseller.id)

        data = {
            "id":id,
            "total_leads": leads_base.count(),
            "total_won_leads": leads_base.filter(Lead.status == "won").count(),
            "total_lost_leads": leads_base.filter(Lead.status == "lost").count(),
        }
        data["total_pending_leads"] = data["total_leads"] - data["total_won_leads"] - data["total_lost_leads"]
        data["total_win_rate"] = round((data["total_won_leads"] / data["total_leads"]) * 100, 2)
        for i in range(0,4):
            month = leads_base\
                .filter(and_(
                        Lead.datetime >= datetime.date(now.year, now.month - i, 1),
                        Lead.datetime < datetime.date(now.year, now.month - i + 1, 1)
                    )
                )
            data["month-" + str(i)] = {}
            data["month-" + str(i)]["total_leads"] = month.count()
            data["month-" + str(i)]["total_won_leads"] = month.filter(Lead.status == "won").count()
            data["month-" + str(i)]["total_lost_leads"] = month.filter(Lead.status == "lost").count()
            data["month-" + str(i)]["total_pending_leads"] = data["month-" + str(i)]["total_leads"] \
                                                           - data["month-" + str(i)]["total_won_leads"] \
                                                           - data["month-" + str(i)]["total_lost_leads"]
            data["month-" + str(i)]["total_win_rate"] = round((data["month-" + str(i)]["total_won_leads"] / data["month-" + str(i)]["total_leads"]) * 100, 2)
        return {"status":"success",
                "data": data}

