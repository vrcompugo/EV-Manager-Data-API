from flask import request
from flask_restplus import Resource
from flask_restplus import Namespace, fields
from luqum.parser import parser

from app.decorators import token_required, api_response

from .file_services import sync_item, update_item, get_items, get_one_item


api = Namespace('File')
_item_input = api.model("File_", model={
})


@api.route('/')
class Items(Resource):

    @api_response
    @api.expect(_item_input)
    #@token_required("create_file")
    def post(self):
        data = {
            "filename": request.form.get("filename"),
            "uuid": request.form.get("uuid"),
            "content-type": request.form.get("content-type"),
            "file": request.files["file"]
        }
        print(data)
        item = sync_item(data=data)
        item_dict = get_one_item(id=item.id)
        return {"status":"success",
                "data": item_dict}


@api.route('/<id>')
class User(Resource):
    @api_response
    @api.doc(params={
        "fields": {"type":"string", "default": "_default_"},
    })
    @token_required("show_project")
    def get(self, id):
        """get a project given its identifier"""
        fields = request.args.get("fields") or "_default_"
        item_dict = get_one_item(id, fields)
        if not item_dict:
            api.abort(404)
        else:
            return {"status":"success",
                "data": item_dict}

    @api.response(201, 'User successfully updated.')
    @api.doc('update project')
    @api.expect(_item_input, validate=True)
    @token_required("update_project")
    def put(self, id):
        """Update User """
        data = request.json
        return update_item(id, data=data)
