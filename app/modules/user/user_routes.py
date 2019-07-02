from flask import request
from flask_restplus import Resource
from flask_restplus import Namespace, fields
from app.decorators import token_required, api_response
from luqum.parser import parser

from .user_services import *
from .models import UserRole
from app.modules.auth.auth_services import get_logged_in_user

api = Namespace('Users')
api2 = Namespace('UserRoles')

_user_input = api.model("User_", model={
    'email': fields.String(required=True, description='user email address'),
    'username': fields.String(required=True, description='user username'),
    'password': fields.String(required=True, description='user password'),
    'roles': fields.List(required=True, description='', cls_or_instance=fields.Integer())
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
    @token_required("list_user")
    def get(self):
        """
            List users
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
        data = get_items(tree, sort, offset, limit, fields)
        return {"status":"success",
                "fields": fields,
                "sort": sort,
                "offset": offset,
                "limit": limit,
                "query": query,
                "data": data}

    @api_response
    @api.expect(_user_input, validate=True)
    @token_required("create_user")
    def post(self):
        """Creates a new User """
        data = request.json
        user = get_logged_in_user(request)
        if "roles" in data:
            root_role = UserRole.query.filter(UserRole.code == "root").first()
            if root_role.id in data["roles"] and "create_root_user" != user["permissions"]:
                raise ApiException("invalid_permission", "Invalid Permission.", 401)
        item = add_item(data=data)
        item_dict = get_one_item(item.id)
        return {"status":"success",
                "data": item_dict}


@api.route('/<id>')
class User(Resource):
    @api_response
    @api.doc(params={
        "fields": {"type":"string", "default": "_default_"},
    })
    @token_required("show_user")
    def get(self, id):
        """get a user given its identifier"""
        fields = request.args.get("fields") or "_default_"
        item_dict = get_one_item(id, fields)
        if not item_dict:
            api.abort(404)
        else:
            return item_dict

    @api.response(201, 'User successfully updated.')
    @api.doc('update user')
    @api.expect(_user_input, validate=True)
    @token_required("update_user")
    def put(self, id):
        """Update User """
        data = request.json
        user = get_logged_in_user(request)
        if "roles" in data:
            root_role = UserRole.query.filter(UserRole.code == "root").first()
            if root_role.id in data["roles"] and "create_root_user" != user["permissions"]:
                raise ApiException("invalid_permission", "Invalid Permission.", 401)
        return update_item(id, data=data)


@api2.route('/')
class Items2(Resource):
    @api_response
    @token_required("list_user_roles")
    def get(self):
        data = get_role_items()
        return {"status": "success",
                "data": data}
