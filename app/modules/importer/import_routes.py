from flask import request
from flask_restplus import Resource
from flask_restplus import Namespace, fields
from luqum.parser import parser

from app.decorators import token_required, api_response

from .import_services import import_by_source_module, get_items


api = Namespace('Import')
_item_input = api.model("ImportRequest_", model={
    "source": fields.String(required=True, description=''),
    "model": fields.String(required=True, description=''),
    "remote_id": fields.Integer(description=''),
    "local_id": fields.Integer(description=''),
})


@api.route('/')
class Items(Resource):

    #@api_response
    @api.expect(_item_input, validate=True)
    #@token_required("create_file")
    def post(self):
        data = request.json
        print(data)
        if "remote_id" in data and data["remote_id"] != 0:
            import_by_source_module(source=data["source"], model=data["model"], remote_id=data["remote_id"])
            return {"status": "success"}
        if "local_id" in data and data["local_id"] != 0:
            import_by_source_module(source=data["source"], model=data["model"], local_id=data["local_id"])
            return {"status": "success"}
        import_by_source_module(source=data["source"], model=data["model"])
        return {"status":"success"}

    @api_response
    @api.doc(params={
        'offset': {"type":'integer', "default": 0},
        "limit":{"type":'integer', "default": 10},
        "sort": {"type":"string", "default": ""},
        "fields": {"type":"string", "default": "_default_"},
        "q": {"type":"string", "default": "", "description": "Lucene syntax search query"}
    })
    @token_required("list_lead")
    def get(self):
        """
            List leads
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
