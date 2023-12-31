from flask import request
from flask_restplus import Resource
from flask_restplus import fields
from app.decorators import token_required, api_response
from luqum.parser import parser

from ._customer_ns import api
from ..services.customer_payment_account_services import *


_item_input = api.model("CustomerPaymentAccount_", model={
    'type': fields.String(required=True, description=''),
    'data': fields.Raw(required=True, description=''),
})


@api.route('/<customer_id>/payment_accounts')
class Index(Resource):

    @api_response
    @api.doc(params={
        'offset': {"type":'integer', "default": 0},
        "limit":{"type":'integer', "default": 10},
        "sort": {"type":"string", "default": ""},
        "fields": {"type":"string", "default": "_default_"},
        "q": {"type":"string", "default": "", "description": "Lucene syntax search query"}
    })
    @token_required("list_customer_payment_account")
    def get(self):
        """
            List customers
            sort:
                - "column1,column2" -> column1 asc, column2 asc
                - "+column1,-column2" -> column1 asc, column2 desc
            fields:
                Filter output to only needed fields
                - "column1,column2" -> {column1: "", column2: ""}

        """
        offset = int(request.args.get("offset")) or 0
        limit = int(request.args.get("limit")) or 10
        sort = request.args.get("sort") or ""
        fields = request.args.get("fields") or "_default_"
        query = request.args.get("q") or None
        tree = None
        if query is not None:
            tree = parser.parse(query)
        data, total_count = get_items(tree, sort, offset, limit, fields)
        return {"status":"success",
                "fields": fields,
                "sort": sort,
                "offset": offset,
                "limit": limit,
                "query": query,
                "total_count": total_count,
                "data": data}

    @api_response
    @api.expect(_item_input, validate=True)
    @token_required("create_customer_payment_account")
    def post(self):
        """Create new Customer """
        data = request.json
        item = add_item(data=data)
        item_dict = get_one_item(item.id)
        return {"status":"success",
                "data": item_dict}


@api.route('/<customer_id>/payment_accounts/<id>')
class Detail(Resource):
    @api_response
    @api.doc(params={
        "fields": {"type":"string", "default": "_default_"},
    })
    @token_required("show_customer_payment_account")
    def get(self, id):
        """get one customer by id"""
        fields = request.args.get("fields") or "_default_"
        item_dict = get_one_item(id, fields)
        if item_dict is None:
            api.abort(404)
        else:
            return {"status":"success",
                "data": item_dict}

    @api_response
    @api.expect(_item_input, validate=True)
    @token_required("update_customer_payment_account")
    def put(self, id):
        """update one customer by id"""
        item = get_one_item(id)
        if item is None:
            api.abort(404)
        else:
            data = request.json
            item = update_item(id, data=data)
            item_dict = get_one_item(item.id, fields)
            return {"status":"success",
                "data": item_dict}

    @api_response
    @token_required("delete_customer_payment_account")
    def delete(self, id):
        """get a user given its identifier"""
        item = get_one_item(id)
        if not item:
            api.abort(404)
        else:
            return item
