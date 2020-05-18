from flask import request
from flask_restplus import Resource
from flask_restplus import Namespace, fields
from sqlalchemy import and_, or_, func
import datetime
from dateutil.relativedelta import relativedelta

from app import db
from app.decorators import token_required, api_response
from app.models import User, UserSchema
from app.modules.importer.sources.bitrix24._association import find_association
from app.modules.auth.auth_services import get_logged_in_user

from .models.calendar_event import CalendarEvent, CalendarEventSchema
from .calendar_services import add_item, update_item


api = Namespace('Calendar')


@api.route('/')
class Items(Resource):

    @api_response
    @api.doc(params={
        'type': {"type": 'string', "default": "day"},
        'search_phrase': {"type": 'string', "default": ""},
        'date': {"type": 'string', "default": None}
    })
    # @token_required("list_lead")
    def get(self):
        user = get_logged_in_user(request)
        if user is None or "roles" not in user:
            return {"status": "error", "message": "auth failed"}
        if len(
            set(user["roles"]).intersection([
                "bookkeeping",
                "construction",
                "construction_lead"])) > 0:
            filter_group = "construction"
        else:
            filter_group = request.args.get("filter_group") or "own"
            if filter_group != "own" and user["id"] not in [1, 2, 13, 18, 77, 107, 104]:
                filter_group = "own"
        cal_type = request.args.get("type") or "day"
        cal_date = request.args.get("date") or str(datetime.date.today())
        search_phrase = request.args.get("search_phrase") or ""

        if cal_type == "day":
            begin_date = datetime.datetime.strptime(cal_date, "%Y-%m-%d")
            end_date = begin_date + datetime.timedelta(days=1)
        if cal_type == "week":
            cal_date = datetime.datetime.strptime(cal_date, "%Y-%m-%d")
            begin_date = cal_date - datetime.timedelta(days=cal_date.weekday())
            end_date = begin_date + datetime.timedelta(weeks=1)
        if cal_type == "month":
            cal_date = datetime.datetime.strptime(cal_date, "%Y-%m-%d")
            begin_date = datetime.datetime(year=cal_date.year, month=cal_date.month, day=1)
            end_date = begin_date + relativedelta(months=+1)
        users = User.query.filter(User.active.is_(True))

        if filter_group == "own":
            users = users.filter(User.id == user["id"])
        if filter_group == "reseller":
            users = users.filter(User.bitrix_department.in_(["Mittendrin statt nur dabei", "Südkurve", "Mittendrin statt nur dabei (HV)"]))
        if filter_group == "eeg":
            users = users.filter(User.bitrix_department.in_(["EEG_EEG"]))
        if filter_group == "construction":
            users = users.filter(User.bitrix_department.in_([
                "Elektrik Abteilung",
                "Montage",
                "Montage ",
                "Montage II (Dach&PV)",
                "Montage III (PV)",
                "Montage Team III",
                "Team Hybrid EnPal",
                "Wärme & Wasser (KEZ)",
                "Service & Wartung"]))
        if filter_group == "service":
            users = users.filter(User.bitrix_department.in_([
                "Technik & Service"]))
        users = users.order_by(User.bitrix_department.asc(), User.name.asc()).all()
        events = CalendarEvent.query.options(
            db.subqueryload("user"),
            db.subqueryload("reseller"),
            db.subqueryload("task"),
            db.subqueryload("order")
        ).filter(
            or_(
                and_(
                    CalendarEvent.begin <= begin_date,
                    CalendarEvent.end >= begin_date
                ),
                and_(
                    CalendarEvent.begin >= begin_date,
                    CalendarEvent.begin < end_date
                )
            )
        )
        if search_phrase != "":
            events = events.filter(func.concat(
                CalendarEvent.company, " ",
                CalendarEvent.firstname, " ",
                CalendarEvent.lastname, " ",
                CalendarEvent.label
            ).ilike('%' + search_phrase + '%'))
        events = events.order_by(CalendarEvent.begin.asc()).all()
        user_schema = UserSchema()
        users = user_schema.dump(users, many=True)
        event_schema = CalendarEventSchema()
        for event in events:
            user = next((user for user in users if user["id"] == event.user_id), None)
            if user is not None:
                event_data = event_schema.dump(event, many=False)
                if event.customer_id is not None:
                    link = find_association("Customer", local_id=event.customer_id)
                    if link is not None:
                        event_data["bitrix_contact_id"] = link.remote_id
                if event.order_id is not None:
                    link = find_association("Order", local_id=event.order_id)
                    if link is not None:
                        event_data["bitrix_order_id"] = link.remote_id
                event_data["user"] = {
                    "name": user["name"],
                    "id": user["id"]
                }
                if event.customer is not None:
                    event_data["customer"] = {
                        "company": event.customer.company,
                        "firstname": event.customer.company,
                        "lastname": event.customer.company,
                        "id": event.customer.id
                    }
                if "events" in user:
                    user["events"].append(event_data)
                else:
                    user["events"] = [event_data]
        data = []
        for user in users:
            if "roles" in user:
                del user["roles"]
            if search_phrase != "" and "events" not in user:
                continue

            departments = user["bitrix_department"].split(",")
            main_department = departments[len(departments) - 1].strip()
            group = next((group for group in data if group["label"] == main_department), None)

            if group is None:
                group = {
                    "label": main_department,
                    "members": [user]
                }
                data.append(group)
            else:
                group["members"].append(user)

        return {"status": "success",
                "boundary": {
                    "begin": str(begin_date),
                    "end": str(end_date),
                },
                "data": data}

    @api_response
    # @token_required("list_lead")
    def post(self):
        item_data = request.json
        data = {
            "label": item_data["label"],
            "comment": item_data["comment"],
            "begin": item_data["begin"],
            "end": item_data["end"],
            "user_id": item_data["user"]["id"],
            "status": "open"
        }
        item = add_item(data=data)
        if "as_task" in item_data and item_data["as_task"]:
            # add task
            pass
        return {"status": "success"}


@api.route('/<id>')
class Item(Resource):

    @api_response
    # @token_required("list_lead")
    def put(self, id):
        item_data = request.json
        data = {
            "label": item_data["label"],
            "comment": item_data["comment"],
            "begin": item_data["begin"],
            "end": item_data["end"],
            "user_id": item_data["user"]["id"],
        }
        if "order" in item_data and "id" in item_data["order"]:
            data["order_id"] = item_data["order"]["id"]
            if "customer" in item_data["order"]:
                if type(item_data["order"]["customer"]) is int:
                    data["customer_id"] = item_data["order"]["customer"]
                if type(item_data["order"]["customer"]) is dict:
                    data["customer_id"] = item_data["order"]["customer"]["id"]
        item = update_item(id, data=data)
        return {"status": "success"}
