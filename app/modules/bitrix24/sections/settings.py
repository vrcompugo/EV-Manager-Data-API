import jwt
import datetime
from flask import Blueprint, render_template, request, make_response

from app.config import key

from ..utils import get_bitrix_auth_info


def register_routes(api: Blueprint):

    @api.route("/settings/", methods=["GET", "POST"])
    def settings_iframe():
        auth_info = get_bitrix_auth_info(request)
        if "user2" not in auth_info:
            return "Forbidden"
        encoded_jwt = jwt.encode(
            payload={
                'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=3000),
                'iat': datetime.datetime.utcnow(),
                'sub': auth_info["user2"].id
            },
            key=key,
            algorithm='HS256')
        return render_template("settings/iframe.html", encoded_jwt=encoded_jwt.decode())
