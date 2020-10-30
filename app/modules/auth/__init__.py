import requests
import jwt
from flask import request

from .jwt_parser import decode_jwt


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

    data = {
        "auth_code": auth_code,
        "domain": domain,
        "domain_raw": domain_raw,
        "user": None
    }

    if data["domain"] is not None:
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
    return data
