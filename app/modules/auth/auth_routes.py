from flask import request
from flask_restplus import Resource
from flask_restplus import Namespace, fields

from .auth_services import *
from app.decorators import api_response, token_required


api = Namespace('Authentication')
_auth_credentials = api.model('Auth Credentials', {
    'username': fields.String(required=True, description='user username'),
    'password': fields.String(required=True, description='user password')
})


@api.route('/login')
class UserLogin(Resource):

    @api.expect(_auth_credentials, validate=True)
    @api.doc(security=None)
    @api_response
    def post(self):
        """ User Login Resource """
        post_data = request.json
        user = login_user(data=post_data)
        return {"status": "success", "data": user}, 200


@api.route('/refresh', methods=["GET", "POST"])
class UserLogin(Resource):
    @api_response
    @token_required()
    def get(self):
        """ User Login Resource """
        user = revalidate_user()
        return {"status": "success", "data": user}, 200

    @api_response
    @token_required()
    def post(self):
        """ User Login Resource """
        user = revalidate_user()
        return {"status": "success", "data": user}, 200
