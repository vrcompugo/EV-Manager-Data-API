import datetime
from flask import request
from flask_restplus import Resource
from flask_restplus import Namespace, fields

from app.decorators import token_required, api_response
from app.modules.auth.auth_services import get_logged_in_user
from app.modules.offer.offer_services import add_item_v2, update_item_v2, get_one_item_v2
from app.models import OfferV2, Reseller

from .services.offer import get_offer_by_offer_number
from .services.calculation import calculate_cloud, get_cloud_products


api = Namespace('Cloud')


@api.route('/calculation')
class Items(Resource):

    @api_response
    @token_required("cloud_calculation")
    def post(self):
        """ Stores new offer """
        data = request.json
        calucalted = calculate_cloud(data)
        return {"status": "success",
                "data": calucalted}


@api.route('/offer')
class Items(Resource):

    @api_response
    @token_required("cloud_calculation")
    def post(self):
        data = request.json
        calculated = calculate_cloud(data)
        items = get_cloud_products(data=data)
        offer_v2_data = {
            "reseller_id": None,
            "offer_group": "cloud-offer",
            "datetime": datetime.datetime.now(),
            "currency": "eur",
            "tax_rate": 16,
            "subtotal": calculated["cloud_price"],
            "subtotal_net": calculated["cloud_price"] / 1.16,
            "shipping_cost": 0,
            "shipping_cost_net": 0,
            "discount_total": 0,
            "total_tax": calculated["cloud_price"] * 0.16,
            "total": calculated["cloud_price"],
            "status": "created",
            "data": data,
            "calculated": calculated,
            "items": items
        }
        user = get_logged_in_user()
        reseller = Reseller.query.filter(Reseller.user_id == user["id"]).first()
        if reseller is not None:
            offer_v2_data["reseller_id"] = reseller.id
        item = add_item_v2(data=offer_v2_data)
        item_dict = get_one_item_v2(item.id)
        if item.pdf is not None:
            item_dict["pdf_link"] = item.pdf.public_link
        return {"status": "success",
                "data": item_dict}


@api.route('/offer/<offer_number>')
class User(Resource):
    @api_response
    @token_required("cloud_calculation")
    def get(self, offer_number):
        """get a contract given its identifier"""
        fields = request.args.get("fields") or "_default_"
        offer = get_offer_by_offer_number(offer_number)
        if offer is None:
            api.abort(404)
        item_dict = get_one_item_v2(offer.id, fields)
        if item_dict is None:
            api.abort(404)
        if offer.pdf is not None:
            item_dict["pdf_link"] = offer.pdf.public_link
        print(item_dict)
        return {
            "status": "success",
            "data": item_dict
        }

    @api_response
    @token_required("cloud_calculation")
    def put(self, offer_number):
        from app.modules.offer.services.pdf_generation.offer import generate_offer_pdf

        offer = get_offer_by_offer_number(offer_number)
        if offer is None:
            api.abort(404)
        data = request.json
        calculated = calculate_cloud(data)
        items = get_cloud_products(data={
            "data": data,
            "calculated": calculated
        })
        offer_v2_data = {
            "datetime": datetime.datetime.now(),
            "subtotal": calculated["cloud_price"],
            "subtotal_net": calculated["cloud_price"] / 1.16,
            "total_tax": calculated["cloud_price"] * 0.16,
            "total": calculated["cloud_price"],
            "data": data,
            "calculated": calculated,
            "items": items
        }
        item = update_item_v2(id=offer.id, data=offer_v2_data)
        generate_offer_pdf(item)
        item_dict = get_one_item_v2(item.id)
        if item.pdf is not None:
            item_dict["pdf_link"] = item.pdf.public_link
        return {"status": "success",
                "data": item_dict}
