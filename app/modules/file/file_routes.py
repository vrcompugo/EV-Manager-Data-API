from flask import request, make_response
from flask_restplus import Resource, reqparse
from flask_restplus import Namespace, fields
import werkzeug
import base64
import requests
from luqum.parser import parser

from app.decorators import token_required, api_response
from app.exceptions import ApiException
from app.modules.auth.jwt_parser import decode_jwt
from app.modules.external.bitrix24.drive import get_file

from .file_services import sync_item, update_item, get_items, get_one_item, decode_file_token, S3File


api = Namespace('File')
_item_input = api.model("File_", model={
    'company': fields.String(required=True, description=''),
})
file_upload = reqparse.RequestParser()
file_upload.add_argument('file',
                         type=werkzeug.datastructures.FileStorage,
                         location='files',
                         required=True,
                         help='File')
file_upload.add_argument('filename',
                         type=str,
                         required=True,
                         help='')
file_upload.add_argument('filename',
                         type=str,
                         required=False,
                         help='')


@api.route('/')
class Items(Resource):

    @api_response
    @api.expect(file_upload)
    @token_required()
    def post(self):
        filename = request.form.get("filename")
        if filename is None:
            filename = request.files["file"].filename
        data = {
            "filename": filename,
            "content-type": request.files["file"].content_type,
            "file": request.files["file"]
        }
        item = sync_item(data=data)
        item_dict = get_one_item(id=item.id)
        return {"status": "success",
                "data": item_dict}


@api.route('/<id>')
class User(Resource):
    @api_response
    @api.doc(params={
        "fields": {"type": "string", "default": "_default_"},
    })
    @token_required("show_project")
    def get(self, id):
        """get a project given its identifier"""
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
    @api.doc('update project')
    @api.expect(_item_input, validate=True)
    @token_required("update_project")
    def put(self, id):
        """Update User """
        data = request.json
        return update_item(id, data=data)


@api.route("/view/<token>")
class ViewFile(Resource):
    def get(self, token):
        #try:
        data = decode_jwt(token)
        file = get_file(data["file_id"])
        r = requests.get(file["DOWNLOAD_URL"])
        response = make_response(r.content)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = \
            'inline; filename=%s' % file["NAME"]
        return response
        #except Exception as e:
        #    pass

        token = base64.b64decode(token.encode('utf-8'))
        try:
            data = decode_file_token(token)
            file = S3File.query.get(data["id"])
            if file is None:
                return "not found"
        except Exception as e:
            return "not found"
        content = file.get_file().read()
        response = make_response(content)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = \
            'inline; filename=%s' % file.filename
        return response
