from flask import request
from flask_restplus import Resource
from flask_restplus import Namespace, fields

from app.decorators import token_required, api_response

from .import_services import import_by_source_module


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
        if "remote_id" in data and data["remote_id"] != 0:
            import_by_source_module(source=data["source"], model=data["model"], remote_id=data["remote_id"])
            return {"status": "success"}
        if "local_id" in data and data["local_id"] != 0:
            import_by_source_module(source=data["source"], model=data["model"], local_id=data["local_id"])
            return {"status": "success"}
        import_by_source_module(source=data["source"], model=data["model"])
        return {"status":"success"}
