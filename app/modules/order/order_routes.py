from flask import request
from flask_restplus import Resource
from flask_restplus import Namespace, fields
from luqum.parser import parser

from app import db
from app.decorators import token_required, api_response

from .order_services import get_items


api = Namespace('Order')


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
