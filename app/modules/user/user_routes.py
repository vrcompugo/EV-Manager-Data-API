import json
from flask import Blueprint, Response, request, render_template

from app import db
from app.modules.auth import validate_jwt, get_auth_info
from app.modules.auth.jwt_parser import encode_jwt
from app.modules.external.bitrix24.user import get_users_per_department
from app.modules.settings import get_settings
from app.models import UserZipAssociation


blueprint = Blueprint("users", __name__, template_folder='templates')


@blueprint.route("sales_users", methods=['GET'])
def sales_users():
    auth_data = validate_jwt()
    if auth_data is None or "user" not in auth_data or auth_data["user"] is None:
        return "forbidden", 401
    users = []
    defaults = {
        "data": [],
        "user_type": "Handelsvertreter 2022"
    }
    departments = [
        5,   # Vertrieb
        23,  # VK Profis E360
        57,  # HV Profis E360
        43,  # ---
        248,  # Team POWER-PLAY
        272,  # ---
        270,  # ---
        41,   # Extern IT Unterstützung
        390,  # Team Power Play 2022
        434,   # Team Dura
        432,   # Team Gode
        436,   # Team Herzberg
        392,   # Team Hoffmann
        428,   # Team Kraft
        386,   # Team Maier
        430,   # Team Miele
        426,   # Team Niggemann
        384    # Team Schuster
    ]
    for department_id in departments:
        response = get_users_per_department(department_id)  # Verkauf/Außendienst
        if response is None:
            continue
        for user in response:
            existing_user = next((item for item in users if str(item["ID"]) == str(user["ID"])), None)
            if existing_user is not None:
                continue
            if user["NAME"] is None or user["NAME"] == "":
                user["NAME"] = user["EMAIL"]
            association = UserZipAssociation.query.filter(UserZipAssociation.user_id == user["ID"]).first()
            if association is None:
                user["association"] = defaults
            else:
                if association.user_type in [None, ""]:
                    association.user_type = defaults["user_type"]
                user["association"] = {
                    "data": association.data,
                    "last_assigned": str(association.last_assigned),
                    "max_leads": association.max_leads,
                    "current_cycle_index": association.current_cycle_index,
                    "current_cycle_count": association.current_cycle_count,
                    "supervisor_id": association.supervisor_id,
                    "user_type": association.user_type
                }
                if user["association"]["last_assigned"] == "None":
                    user["association"]["last_assigned"] = None
            if user["ACTIVE"] is True or user["ACTIVE"] == "true" or user["association"].get("max_leads", 0) > 0:
                users.append(user)
    users.sort(key=lambda x: x["NAME"], reverse=True)
    users.reverse()
    return Response(
        json.dumps({"status": "success", "data": users}),
        status=200,
        mimetype='application/json')


@blueprint.route("sales_users", methods=['POST'])
def sales_users_store():
    auth_data = validate_jwt()
    if auth_data is None or "user" not in auth_data or auth_data["user"] is None:
        return "forbidden", 401
    data = request.json
    association = UserZipAssociation.query.filter(UserZipAssociation.user_id == data["ID"]).first()
    if association is None:
        association = UserZipAssociation(
            user_id=int(data["ID"]),
            current_cycle_count=0,
            comment=f"{data['NAME']} {data['LAST_NAME']}"
        )
        db.session.add(association)
    association.data = data["association"]["data"]
    if "max_leads" not in data["association"] or data["association"]["max_leads"] is None or data["association"]["max_leads"] == "":
        data["association"]["max_leads"] = 0
    association.max_leads = int(data["association"]["max_leads"])
    if "supervisor_id" in data["association"] and data["association"]["supervisor_id"] is not None:
        association.supervisor_id = int(data["association"]["supervisor_id"])
    association.user_type = data["association"].get("user_type")
    db.session.commit()
    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


@blueprint.route("supervisors", methods=['GET'])
def supervisors():
    auth_data = validate_jwt()
    if auth_data is None or "user" not in auth_data or auth_data["user"] is None:
        return "forbidden", 401
    users = []
    departments = [
        5,   # Vertrieb
        23,  # VK Profis E360
        57,  # HV Profis E360
        43,  # ---
        248,  # Team POWER-PLAY
        272,  # ---
        270,  # ---
        41,  # Extern IT Unterstützung
        390,  # Team Power Play 2022
        434,   # Team Dura
        432,   # Team Gode
        436,   # Team Herzberg
        392,   # Team Hoffmann
        428,   # Team Kraft
        386,   # Team Maier
        430,   # Team Miele
        426,   # Team Niggemann
        384    # Team Schuster
    ]
    for department_id in departments:
        response = get_users_per_department(department_id)  # Verkauf/Außendienst
        if response is None:
            continue
        for user in response:
            existing_user = next((item for item in users if str(item["ID"]) == str(user["ID"])), None)
            if existing_user is not None:
                continue
            association = UserZipAssociation.query.filter(UserZipAssociation.user_id == user["ID"]).first()
            if association is None:
                continue
            if association.user_type not in ["Ausbilder", "Teamleiter HV", "Teamleiter Angestellt"]:
                continue
            user["fullname"] = user["NAME"] + " " + user["LAST_NAME"]
            user["ID"] = int(user["ID"])
            if user["ACTIVE"] is True or user["ACTIVE"] == "true":
                users.append(user)
    users.sort(key=lambda x: x["NAME"], reverse=True)
    users.append({
        "fullname": "Kein Teamleiter",
        "ID": 0
    })
    users.reverse()
    return Response(
        json.dumps({"status": "success", "data": users}),
        status=200,
        mimetype='application/json')


@blueprint.route("sales_settings", methods=['GET', 'POST'])
def sales_users_settings_app():
    config = get_settings(section="external/bitrix24")
    auth_info = get_auth_info()
    if auth_info["user"] is None:
        return "Forbidden"
    token = encode_jwt(auth_info, expire_minutes=600)
    return render_template("sales_settings/sales_settings.html", token=token)
