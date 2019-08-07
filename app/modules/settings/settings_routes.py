from flask import request
from flask_restplus import Resource
from flask_restplus import Namespace, fields
from luqum.parser import parser

from app.decorators import token_required, api_response

from .settings_services import add_item, update_item, get_items, get_one_item


api = Namespace('Settings')
_item_input = api.model("Settings_", model={
    'section': fields.String(description=''),
    'data': fields.Raw(description='')
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
    @token_required("list_settings")
    def get(self):
        """
            List settingss
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
    @token_required("create_settings")
    def post(self):
        """Creates a new User """
        data = request.json
        item = add_item(data=data)
        if item is None:
            return {"status": "error", "code": "not-found", "message": "Item not found"}, 404
        item_dict = get_one_item(item.section)
        return {"status":"success",
                "data": item_dict}


@api.route('/<section>')
class User(Resource):
    @api_response
    @api.doc(params={
        "fields": {"type":"string", "default": "_default_"},
    })
    @token_required("show_settings")
    def get(self, section):
        """get a settings given its identifier"""
        fields = request.args.get("fields") or "_default_"
        item_dict = get_one_item(section, fields)
        if not item_dict:
            return {"status": "error", "code": "not-found", "message": "Item not found"}, 404
        else:
            return {"status":"success",
                "data": item_dict}

    @api.response(201, 'User successfully updated.')
    @api.doc('update settings')
    @api.expect(_item_input, validate=True)
    @token_required("update_settings")
    def put(self, section):
        """Update User """
        data = request.json
        item = update_item(section, data=data)
        if item is None:
            return {"status": "error", "code": "not-found", "message": "Item not found"}, 404
        else:
            item_dict = get_one_item(item.section)
            return {"status":"success",
                    "data": item_dict}
