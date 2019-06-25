from flask import request
from flask_restplus import Resource
from flask_restplus import Namespace, fields
from app.decorators import token_required

from ._customer_ns import api
from app.modules.user.user_services import *


_item_input = api.model("CustomerAddress_", model={
    'company': fields.String(required=True, description=''),
    'salutation': fields.String(required=True, description=''),
    'title': fields.String(required=True, description=''),
    'firstname': fields.String(required=True, description=''),
    'lastname': fields.String(required=True, description=''),
    'street': fields.String(required=True, description=''),
    'street_nb': fields.String(required=True, description=''),
    'street_extra': fields.String(required=True, description=''),
    'zip': fields.String(required=True, description=''),
    'city': fields.String(required=True, description='')
})


_item_output = api.model("CustomerAddress", model={
    'email': fields.String(description='user email address'),
    'username': fields.String(description='user username'),
    'registered_on': fields.String(description='registered_on'),
    'public_id': fields.String(description='user Identifier')
})


@api.route('/<customer_id>/addresses')
@api.param('customer_public_id', 'The Customer ID')
class Index(Resource):
    @api.marshal_list_with(_item_output, envelope='data')
    @token_required
    def get(self):
        """List all registered customers"""
        return get_all_items()

    @api.response(201, 'User successfully loaded.')
    @api.doc('add new customer address')
    @api.expect(_item_input, validate=True)
    @token_required
    def post(self):
        """Load a new Customer by Customer number/Lead Number/E-Mail """
        data = request.json
        return save_new_item(data=data)


@api.route('/<customer_id>/addresses/<customer_address_id>')
@api.param('customer_public_id', 'The Customer ID')
@api.param('customer_address_public_id', 'The Customer ID')
@api.response(404, 'Address not found.')
class Detail(Resource):
    @api.doc('get customer address data')
    @api.marshal_with(_item_output)
    @token_required
    def get(self, public_id):
        """get a user given its identifier"""
        user = get_one_item(public_id)
        if not user:
            api.abort(404)
        else:
            return user

    @api.doc('update customer address data')
    @api.marshal_with(_item_output)
    @token_required
    def put(self, public_id):
        """get a user given its identifier"""
        user = get_one_item(public_id)
        if not user:
            api.abort(404)
        else:
            return user

    @api.doc('delete customer address')
    @api.marshal_with(_item_output)
    @token_required
    def delete(self, public_id):
        """get a user given its identifier"""
        user = get_one_item(public_id)
        if not user:
            api.abort(404)
        else:
            return user
