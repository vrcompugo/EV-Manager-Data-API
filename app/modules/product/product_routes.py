from flask import request
from flask_restplus import Resource
from flask_restplus import Namespace, fields
from luqum.parser import parser

from app.decorators import token_required, api_response

from .product_services import add_item, update_item, get_items, get_one_item


api = Namespace('Product')
_item_input = api.model("Product_", model={
    'datetime': fields.DateTime(description=''),
    'reminder_datetime': fields.DateTime(description=''),
    'description': fields.String(description=''),
    'customer_id': fields.Integer(description=''),
    'role_id': fields.Integer(description=''),
    'reseller_id': fields.Integer(description=''),
    'product_id': fields.Integer(description=''),
    'offer_id': fields.Integer(description=''),
    'project_id': fields.Integer(description=''),
    'contract_id': fields.Integer(description=''),
    'pv_system_id': fields.Integer(description=''),
    'product_id': fields.Integer(description='')
})


@api.route('/')
class Items(Resource):
    @api_response
    @api.doc(params={
        'offset': {"type":'integer', "default": 0},
        "limit":{"type":'integer', "default": 10},
        "sort": {"type":"string", "default": ""},
        "fields": {"type":"string", "default": "_default_"},
        "q": {"type":"string", "default": "", "description": "Lucene syntax search query"}
    })
    @token_required("list_product")
    def get(self):
        """
            List products
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
        data = get_items(tree, sort, offset, limit, fields)
        return {"status":"success",
                "fields": fields,
                "sort": sort,
                "offset": offset,
                "limit": limit,
                "query": query,
                "data": data}

    @api_response
    @api.expect(_item_input, validate=True)
    @token_required("create_product")
    def post(self):
        """Creates a new User """
        data = request.json
        item = add_item(data=data)
        item_dict = get_one_item(item.id)
        return {"status":"success",
                "data": item_dict}


@api.route('/<id>')
class User(Resource):
    @api_response
    @api.doc(params={
        "fields": {"type":"string", "default": "_default_"},
    })
    @token_required("show_product")
    def get(self, id):
        """get a product given its identifier"""
        fields = request.args.get("fields") or "_default_"
        item_dict = get_one_item(id, fields)
        if not item_dict:
            api.abort(404)
        else:
            return item_dict

    @api.response(201, 'User successfully updated.')
    @api.doc('update product')
    @api.expect(_item_input, validate=True)
    @token_required("update_product")
    def put(self, id):
        """Update User """
        data = request.json
        return update_item(id, data=data)
