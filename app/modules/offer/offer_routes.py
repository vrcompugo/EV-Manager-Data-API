import json
from flask import request
from sqlalchemy import or_
from flask_restplus import Resource
from flask_restplus import Namespace, fields
from luqum.parser import parser

from app import db
from app.decorators import token_required, api_response
from app.models import OfferV2
from app.modules.auth import get_auth_info, validate_jwt

from .offer_services import add_item, update_item, get_items, get_one_item, generate_cloud_pdf, generate_feasibility_study_pdf, generate_offer_pdf, get_one_item_v2


api = Namespace('Offer')
_item_input = api.model("Offer_", model={
    'product_number': fields.String(description=''),
    'survey_id': fields.Integer(description=''),
    'customer_id': fields.Integer(description=''),
    'address_id': fields.Integer(description=''),
    'payment_account_id': fields.Integer(description=''),
    'reseller_id': fields.Integer(description=''),
    'datetime': fields.DateTime(description=''),
    'status': fields.String(description=''),
    'data': fields.Raw(description=''),
    'price_definition': fields.Raw(description='')
})


@api.route('/')
class Items(Resource):
    @api_response
    @api.doc(params={
        'offset': {"type": 'integer', "default": 0},
        "limit": {"type": 'integer', "default": 10},
        "sort": {"type": "string", "default": ""},
        "fields": {"type": "string", "default": "_default_"},
        "q": {"type": "string", "default": "", "description": "Lucene syntax search query"}
    })
    @token_required("list_offer")
    def get(self):
        """
            List offers
            sort:
                - "column1,column2" -> column1 asc, column2 asc
                - "+column1,-column2" -> column1 asc, column2 desc
            fields:
                Filter output to only needed fields
                - "column1,column2" -> {column1: "", column2: ""}

        """
        offset = int(request.args.get("offset") or 0)
        limit = int(request.args.get("limit") or 10)
        sort = request.args.get("sort") or ""
        fields = request.args.get("fields") or "_default_"
        query = request.args.get("q") or None
        tree = None
        if query is not None:
            tree = parser.parse(query)
        data, total_count = get_items(tree, sort, offset, limit, fields)
        return {"status": "success",
                "fields": fields,
                "sort": sort,
                "offset": offset,
                "limit": limit,
                "query": query,
                "total_count": total_count,
                "data": data}

    @api_response
    @api.expect(_item_input, validate=True)
    @token_required("create_offer")
    def post(self):
        """Creates a new User """
        data = request.json
        item = add_item(data=data)
        item_dict = get_one_item(item.id)
        return {"status": "success",
                "data": item_dict}


@api.route('/<id>')
class User(Resource):
    @api_response
    @api.doc(params={
        "fields": {"type": "string", "default": "_default_"},
    })
    @token_required("show_offer")
    def get(self, id):
        """get a offer given its identifier"""
        fields = request.args.get("fields") or "_default_"
        item_dict = get_one_item(id, fields)
        if not item_dict:
            api.abort(404)
        else:
            return {
                "status": "success",
                "data": item_dict
            }

    @api.response(201, 'User successfully updated.')
    @api.doc('update offer')
    @api.expect(_item_input, validate=True)
    @token_required("update_offer")
    def put(self, id):
        """Update User """
        data = request.json
        return update_item(id, data=data)


@api.route('/v2/<quote_number>')
class User(Resource):
    @api_response
    def get(self, quote_number):
        auth_info = get_auth_info()
        if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
            return {"status": "error", "error_code": "not_authorized", "message": "user not authorized for this action"}
        fields = request.args.get("fields") or "_default_"
        offer = OfferV2.query.filter(OfferV2.number == quote_number).first()
        if offer is None:
            if quote_number.find("-") < 0:
                return {"status": "error", "error_code": "not_found", "message": "Angebot nicht gefunden"}, 404
            quote_number_parts = quote_number.split("-")
            try:
                quote_id = int(quote_number_parts[len(quote_number_parts) - 1].strip())
            except:
                return {"status": "error", "error_code": "not_found", "message": "Angebot nicht gefunden"}, 404
            offer = OfferV2.query.filter(OfferV2.id == quote_id).first()
            if offer is None:
                return {"status": "error", "error_code": "not_found", "message": "Angebot nicht gefunden"}, 404
        if offer is None:
        item_dict = offer.to_dict()
        item_dict["pdf_link"] = offer.pdf.public_link if offer.pdf is not None else None
        item_dict["data_txt"] = json.dumps(item_dict.get("data"), indent=4)
        item_dict["calculated_txt"] = json.dumps(item_dict.get("calculated"), indent=4)
        if not item_dict:
            api.abort(404)
        else:
            return {
                "status": "success",
                "data": item_dict
            }

    @api.response(201, 'User successfully updated.')
    @api.doc('update offer')
    @api_response
    def put(self, quote_number):
        auth_info = get_auth_info()
        if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
            return {"status": "error", "error_code": "not_authorized", "message": "user not authorized for this action"}
        data = request.json
        offer = OfferV2.query.filter(OfferV2.number == quote_number).first()
        if offer is None:
            return {"status": "error", "error_code": "not_found", "message": "Angebot nicht gefunden"}, 404
        offer.data = json.loads(data.get("data_txt"))
        offer.calculated = json.loads(data.get("calculated_txt"))
        db.session.commit()
        return self.get(quote_number)


@api.route('/<id>/PDF')
class OfferPDF(Resource):
    def get(self, id):
        from app.modules.offer.services.pdf_generation.feasibility_study import generate_feasibility_study_pdf
        from app.modules.offer.services.pdf_generation.cloud_offer import generate_cloud_pdf
        from app.modules.offer.services.pdf_generation.offer import generate_offer_pdf
        offer = OfferV2.query.options(
            db.subqueryload("items"),
            db.subqueryload("customer"),
            db.subqueryload("address")
        ).get(id)
        data = {}
        return generate_cloud_pdf(offer)
        if offer.pdf is not None:
            data["pdf"] = {
                "public_link": offer.pdf.public_link,
                "filename": offer.pdf.filename
            }
        if offer.cloud_pdf is not None:
            data["cloud_pdf"] = {
                "public_link": offer.cloud_pdf.public_link,
                "filename": offer.cloud_pdf.filename
            }
        if offer.feasibility_study_pdf is not None:
            data["feasibility_study_pdf"] = {
                "public_link": offer.feasibility_study_pdf.public_link,
                "filename": offer.feasibility_study_pdf.filename
            }
        return data


@api.route('/<id>/PDF2')
class OfferPDF2(Resource):
    def get(self, id):
        from app.modules.offer.services.pdf_generation.feasibility_study import generate_feasibility_study_pdf
        from app.modules.offer.services.pdf_generation.cloud_offer import generate_cloud_pdf
        from app.modules.offer.services.pdf_generation.offer import generate_offer_pdf
        offer = OfferV2.query.options(
            db.subqueryload("items"),
            db.subqueryload("customer"),
            db.subqueryload("address")
        ).get(id)
        data = {}
        return generate_offer_pdf(offer)
        if offer.pdf is not None:
            data["pdf"] = {
                "public_link": offer.pdf.public_link,
                "filename": offer.pdf.filename
            }
        if offer.cloud_pdf is not None:
            data["cloud_pdf"] = {
                "public_link": offer.cloud_pdf.public_link,
                "filename": offer.cloud_pdf.filename
            }
        if offer.feasibility_study_pdf is not None:
            data["feasibility_study_pdf"] = {
                "public_link": offer.feasibility_study_pdf.public_link,
                "filename": offer.feasibility_study_pdf.filename
            }
        return data


@api.route('/<id>/PDF3')
class OfferPDF3(Resource):
    def get(self, id):
        from app.modules.offer.services.pdf_generation.feasibility_study import generate_feasibility_study_pdf
        from app.modules.offer.services.pdf_generation.cloud_offer import generate_cloud_pdf
        from app.modules.offer.services.pdf_generation.offer import generate_offer_pdf
        offer = OfferV2.query.options(
            db.subqueryload("items"),
            db.subqueryload("customer"),
            db.subqueryload("address")
        ).get(id)
        data = {}
        return generate_feasibility_study_pdf(offer, return_string=False)
        if offer.pdf is not None:
            data["pdf"] = {
                "public_link": offer.pdf.public_link,
                "filename": offer.pdf.filename
            }
        if offer.cloud_pdf is not None:
            data["cloud_pdf"] = {
                "public_link": offer.cloud_pdf.public_link,
                "filename": offer.cloud_pdf.filename
            }
        if offer.feasibility_study_pdf is not None:
            data["feasibility_study_pdf"] = {
                "public_link": offer.feasibility_study_pdf.public_link,
                "filename": offer.feasibility_study_pdf.filename
            }
        return data


@api.route('/<id>/PDF4')
class OfferPDF3(Resource):
    def get(self, id):
        from app.modules.offer.services.pdf_generation.feasibility_study import generate_feasibility_study_2020_pdf
        offer = OfferV2.query.options(
            db.subqueryload("items"),
            db.subqueryload("customer"),
            db.subqueryload("address")
        ).get(id)
        data = {}
        return generate_feasibility_study_2020_pdf(offer)
