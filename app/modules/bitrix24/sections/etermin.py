import jwt
import json
import datetime
from flask import Blueprint, render_template, request, make_response

from app.config import key
from app.modules.auth.auth_services import get_logged_in_user
from app.modules.calendar.models.calendar_event import CalendarEvent, CalendarEventSchema
from app.modules.importer.sources.bitrix24._association import find_association

from ..utils import get_bitrix_auth_info


def register_routes(api: Blueprint):

    @api.route("/etermin", methods=["GET", "POST"])
    def etermin_iframe():
        auth_info = get_bitrix_auth_info(request)
        if "user2" not in auth_info:
            return "Forbidden"
        encoded_jwt = jwt.encode(
            payload={
                'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=300),
                'iat': datetime.datetime.utcnow(),
                'sub': auth_info["user2"].id
            },
            key=key,
            algorithm='HS256')
        contact_id = json.loads(request.form.get("PLACEMENT_OPTIONS"))["ID"]
        content = render_template("etermin/iframe2.html", contact_id=contact_id, encoded_jwt=encoded_jwt.decode())
        return content

    @api.route("/etermin/install", methods=["GET", "POST"])
    def etermin_install():
        auth_info = get_bitrix_auth_info(request)
        if "user2" not in auth_info:
            return "Forbidden"
        encoded_jwt = jwt.encode(
            payload={
                'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=300),
                'iat': datetime.datetime.utcnow(),
                'sub': auth_info["user2"].id
            },
            key=key,
            algorithm='HS256')
        return render_template("etermin/install.html", encoded_jwt=encoded_jwt.decode())

    @api.route("/etermin/events/<contact_id>", methods=["GET", "POST"])
    def etermin_events(contact_id):
        auth_info = get_logged_in_user()
        if "user_id" not in auth_info or auth_info["user_id"] <= 0:
            return "Forbidden"
        data = {
            "contact_id": int(contact_id),
            "items": []
        }
        link = find_association("Customer", remote_id=data["contact_id"])
        if link is None:
            return {"status": "customer not found"}, 404, {"Content-Type": "application/json"}
        item_schema = CalendarEventSchema()
        print(link.local_id)
        events = CalendarEvent.query.filter(CalendarEvent.customer_id == link.local_id)
        for event in events:
            data["items"].append(item_schema.dump(event, many=False))
        return data, 200, {"Content-Type": "application/json"}
