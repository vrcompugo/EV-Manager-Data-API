from app.models import User
import datetime
import jwt
from app.config import key
from app.exceptions import ApiException
from flask import request


def encode_auth_token(user_id):
    try:
        payload = {
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=300),
            'iat': datetime.datetime.utcnow(),
            'sub': user_id
        }
        return jwt.encode(
            payload,
            key,
            algorithm='HS256'
        )
    except Exception as e:
        return e


def decode_auth_token(auth_token):
    """
    Decodes the auth token
    :param auth_token:
    :return: integer|string
    """
    try:
        payload = jwt.decode(auth_token, key)
        return payload
    except jwt.ExpiredSignatureError:
        raise ApiException("session_expired", "Signature expired. Please log in again.", 401)
    except jwt.InvalidTokenError:
        raise ApiException("invalid_token", "Invalid token. Please log in again.", 401)


def login_user(data):
    # fetch the user data
    user = User.query.filter_by(username=data.get('username')).first()
    if user and user.check_password(data.get('password')):
        auth_token = encode_auth_token(user.id)
        if auth_token:
            roles = []
            for role in user.roles:
                roles.append(role.code)
            return {"token": auth_token.decode(), "roles": roles}
    else:
        raise ApiException("invalid_credentials", "Invalid Credentials. Please log in again.", 401)


def revalidate_user():
    # fetch the user data
    user = get_logged_in_user(request)
    auth_token = encode_auth_token(user["user_id"])
    if auth_token:
        user["token"] = auth_token.decode()
        return user
    else:
        raise ApiException("invalid_credentials", "Invalid Credentials. Please log in again.", 401)


def get_logged_in_user(new_request=None, auth_token=None):
    from app.modules.auth import get_auth_info
    from app.modules.importer.sources.bitrix24._association import find_association
    # get the auth token
    if auth_token is None:
        bitrix_auth = get_auth_info()
        if bitrix_auth is not None and "user" in bitrix_auth and bitrix_auth["user"] is not None:
            user_link = find_association("User", remote_id=bitrix_auth["user"]["id"])
            if user_link is not None:
                user = User.query.filter(User.id == user_link.local_id).first()
                if user is not None:
                    permission_data = get_user_permission_data(user)
                    return {
                        'id': user.id,
                        'user_id': user.id,
                        'email': user.email,
                        'name': user.name,
                        'bitrix_user_id': user.bitrix_user_id,
                        'bitrix_department': user.bitrix_department,
                        'bitrix_department_ids': user.bitrix_department_ids,
                        'roles': permission_data["roles"],
                        'role_ids': permission_data["role_ids"],
                        'permissions': permission_data["permissions"],
                        'registered_on': str(user.registered_on)
                    }
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
                    'bitrix_department': user.bitrix_department,
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
                'bitrix_department': user.bitrix_department,
                'roles': permission_data["roles"],
                'role_ids': permission_data["role_ids"],
                'permissions': permission_data["permissions"],
                'registered_on': str(user.registered_on)
            }
    raise ApiException("invalid_token", "Invalid Token. Please log in again.", 401)


def get_user_permission_data(user: User):
    roles = []
    role_ids = []
    permissions = []
    for role in user.roles:
        roles.append(role.code)
        role_ids.append(role.id)
        permissions += role.permissions
    return {"roles": roles, "role_ids": role_ids, "permissions": permissions}
