from flask import request
from flask_restplus import Resource, reqparse
from flask_restplus import fields
from app.decorators import token_required, api_response
from luqum.parser import parser
import werkzeug

from ._customer_ns import api
from ..services.customer_file_services import add_item, update_item, get_items, get_one_item


_item_input = reqparse.RequestParser()
_item_input.add_argument('file',
                         type=werkzeug.datastructures.FileStorage,
                         location='files',
                         required=True,
                         help='File')
_item_input.add_argument('filename',
                         type=str,
                         required=True,
                         help='')
_item_input.add_argument('type',
                         type=str,
                         required=True,
                         help='')


@api.route('/<customer_id>/files')
class Index(Resource):

    @api_response
    @api.doc(params={
        'offset': {"type":'integer', "default": 0},
        "limit":{"type":'integer', "default": 10},
        "sort": {"type":"string", "default": ""},
        "fields": {"type":"string", "default": "_default_"},
        "q": {"type":"string", "default": "", "description": "Lucene syntax search query"}
    })
    @token_required("list_customer_file")
    def get(self, customer_id):
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
    @api.expect(_item_input)
    @token_required("create_customer_file")
    def post(self, customer_id):
        """Create new Customer """
        filename = request.form.get("filename") if request.args.get("filename") is None else request.args.get("filename")
        type = request.form.get("type") if request.args.get("type") is None else request.args.get("type")
        data = {
            "customer_number": request.form.get("customer_number"),
            "lead_number": request.form.get("lead_number"),
            "filename": filename,
            "type": type,
            "content-type": request.files["file"].content_type,
            "file": request.files["file"]
        }
        data["customer_id"] = customer_id
        item = add_item(data=data)
        item_dict = get_one_item(item.id)
        return {"status":"success",
                "data": item_dict}


@api.route('/<customer_id>/files/<id>')
class Detail(Resource):
    @api_response
    @api.doc(params={
        "fields": {"type":"string", "default": "_default_"},
    })
    @token_required("show_customer_file")
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
    @token_required("update_customer_file")
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
    @token_required("delete_customer_file")
    def delete(self, id):
        """get a user given its identifier"""
        item = get_one_item(id)
        if not item:
            api.abort(404)
        else:
            return item
