import requests
import jwt
from flask import request

from .jwt_parser import decode_jwt
from app.exceptions import ApiException


def validate_jwt():
    token = request.headers.get("Authorization")
    if token is None:
        return {
            "status": "error",
            "error_code": "token_not_found",
            "message": "Authorization header not found"
        }
    token = token.replace("Bearer ", "")
    try:
        payload = decode_jwt(token)
    except jwt.ExpiredSignatureError:
        return {
            "status": "error",
            "error_code": "token_expired",
            "message": "token expired"
        }
    except jwt.InvalidTokenError:
        return {
            "status": "error",
            "error_code": "token_invalid",
            "message": "token invalid"
        }
    return payload


def get_auth_info():
    domain = None
    domain_raw = None
    auth_code = None
    try:
        auth_info = validate_jwt()
        if "domain" in auth_info:
            return auth_info
    except Exception as e:
        pass
    if request.args.get("token") is not None:
        auth_info = decode_jwt(request.args.get("token"))
        if "domain" in auth_info:
            return auth_info
    if request.args.get("DOMAIN") is not None:
        domain_raw = request.args.get('DOMAIN')
    if request.form.get("auth[domain]") is not None:
        domain_raw = request.form.get('auth[domain]')
    if domain_raw is not None:
        domain = f"https://{domain_raw}"
    if request.args.get("AUTH_ID"):
        auth_code = request.args.get("AUTH_ID")
    if request.form.get("auth[member_id]"):
        auth_code = request.form.get("auth[member_id]")
    if request.form.get("AUTH_ID"):
        auth_code = request.form.get("AUTH_ID")

    user = None
    if domain_raw is None:
        loggend_user = get_logged_in_user()
        if user is not None and "id" in user and user["id"] > 0:
            domain_raw = "keso.bitrix24.de"
            domain = f"https://{domain_raw}"
            user = loggend_user

    data = {
        "auth_code": auth_code,
        "domain": domain,
        "domain_raw": domain_raw,
        "user": user
    }

    if data["domain"] is not None and data["user"] is None:
        x = requests.post(
            data["domain"] + "/rest/user.current.json",
            data={
                "auth": data["auth_code"]
            })
        response_data = x.json()
        if "result" in response_data:
            data["user"] = {}
            for k, v in response_data["result"].items():
                data["user"][k.lower()] = v
    if data.get("user") is not None:
        user = data.get("user")
        data["user"] = {
            "id": user.get("id"),
            "name": user.get("name"),
            "last_name": user.get("last_name"),
            "email": user.get("email"),
            "active": user.get("active"),
            "uf_department": user.get("uf_department")
        }
    return data


def get_logged_in_user(new_request=None, auth_token=None):
    from app.modules.importer.sources.bitrix24._association import find_association
    from .auth_services import decode_auth_token, get_user_permission_data
    from app.modules.user.models.user import User
    # get the auth token
    if new_request is None:
        new_request = request
    if auth_token is None:
        auth_token = new_request.headers.get('Authorization')
    if auth_token:
        auth_token = auth_token.replace("Bearer ", "")
        if auth_token is not None and auth_token != "":
            user = User.query.filter(User.access_key == auth_token).filter(User.active.is_(True)).first()
            if user is not None:
                permission_data = get_user_permission_data(user)
                return {
                    'id': user.id,
                    'user_id': user.id,
                    'email': user.email,
                    'name': user.name,
                    'roles': permission_data["roles"],
                    'role_ids': permission_data["role_ids"],
                    'permissions': permission_data["permissions"],
                    'registered_on': str(user.registered_on)
                }
        resp = decode_auth_token(auth_token)
        user = User.query.filter_by(id=resp.get("sub")).filter(User.active.is_(True)).first()
        if user is not None:
            permission_data = get_user_permission_data(user)
            return {
                'id': user.id,
                'user_id': user.id,
                'email': user.email,
                'name': user.name,
                'roles': permission_data["roles"],
                'role_ids': permission_data["role_ids"],
                'permissions': permission_data["permissions"],
                'registered_on': str(user.registered_on)
            }
    raise ApiException("invalid_token", "Invalid Token. Please log in again.", 401)
