from flask import request
from flask_restplus import Resource
from flask_restplus import Namespace, fields

from .auth_services import *
from . import validate_jwt
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
    @api.doc(security=None)
    @api_response
    def get(self):
        print("lkansc")
        """ User Login Resource """
        try:
            raw = validate_jwt()
            if raw.get("unique_identifier") not in [None, "", 0]:
                return {"status": "success", "data": raw}, 200
        except Exception as e:
            pass
        user = revalidate_user()
        return {"status": "success", "data": user}, 200

    @api_response
    def post(self):
        """ User Login Resource """
        try:
            raw = validate_jwt()
            if raw.get("unique_identifier") not in [None, "", 0]:
                return {"status": "success", "data": raw}, 200
        except Exception as e:
            pass
        user = revalidate_user()
        return {"status": "success", "data": user}, 200
