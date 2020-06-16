from flask import request
from flask_restplus import Resource
from flask_restplus import Namespace, fields

from app.decorators import token_required, api_response
from app.modules.offer.offer_services import add_item_v2, update_item_v2, get_one_item

from .services.offer import get_offer_by_offer_number
from .services.calculation import calculate_cloud


api = Namespace('Cloud')


@api.route('/calculation')
class Items(Resource):

    @api_response
    @token_required("cloud_calculation")
    def post(self):
        """ Stores new offer """
        data = request.json
        calucalted = calculate_cloud(data)
        print(calucalted)
        return {"status": "success",
                "data": calucalted}


@api.route('/offer')
class Items(Resource):

    @api_response
    @token_required("cloud_calculation")
    def post(self):
        data = request.json
        item = add_item_v2(data=data)
        item_dict = get_one_item(item.id)
        return {"status": "success",
                "data": data}


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
        item_dict = get_one_item(offer.id, fields)
        if not item_dict:
            api.abort(404)
        else:
            return {
                "status": "success",
                "data": item_dict
            }

    @api_response
    @token_required("cloud_calculation")
    def put(self, offer_number):
        data = request.json
        offer = get_offer_by_offer_number(offer_number)
        if offer is None:
            api.abort(404)
        update_item_v2(offer.id, data=data)
        item_dict = get_one_item(offer.id, fields)
        return {
            "status": "success",
            "data": item_dict
        }
