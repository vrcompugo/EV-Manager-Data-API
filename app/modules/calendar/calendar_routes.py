from flask import request
from flask_restplus import Resource
from flask_restplus import Namespace, fields
from sqlalchemy import and_, or_
import datetime
from dateutil.relativedelta import relativedelta

from app import db
from app.decorators import token_required, api_response
from app.models import User, UserSchema
from app.modules.importer.sources.bitrix24._association import find_association

from .models.calendar_event import CalendarEvent, CalendarEventSchema


api = Namespace('Calendar')


@api.route('/')
class Items(Resource):

    @api_response
    @api.doc(params={
        'type': {"type": 'string', "default": "day"},
        'date': {"type": 'string', "default": None}
    })
    # @token_required("list_lead")
    def get(self):
        cal_type = request.args.get("type") or "day"
        cal_date = request.args.get("date") or str(datetime.date.today())
        filter_group = request.args.get("filter_group") or "all"

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
        if filter_group == "reseller":
            users = users.filter(User.bitrix_department.in_(["Mittendrin statt nur dabei", "Südkurve", "Mittendrin statt nur dabei (HV)"]))
        if filter_group == "eeg":
            users = users.filter(User.bitrix_department.in_(["EEG_EEG"]))
        if filter_group == "construction":
            users = users.filter(User.bitrix_department.in_([
                "Elektrik Abteilung",
                "Montage",
                "Montage II (Dach&PV)",
                "Montage III (PV)",
                "Montage Team III"]))
        if filter_group == "service":
            users = users.filter(User.bitrix_department.in_([
                "Service & Wartung",
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
        ).order_by(CalendarEvent.begin.asc()).all()

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

                if "events" in user:
                    user["events"].append(event_data)
                else:
                    user["events"] = [event_data]
        data = []
        for user in users:
            if "roles" in user:
                del user["roles"]
            if "events" in user:
                user["max_rows"] = 1
                rows = [datetime.datetime(year=1970, month=1, day=1)]
                for event in user["events"]:
                    event_begin = datetime.datetime.strptime(event["begin"], "%Y-%m-%dT%H:%M:%S")
                    event_end = datetime.datetime.strptime(event["end"], "%Y-%m-%dT%H:%M:%S")
                    row_index = 0
                    found = False
                    for row_end in rows:
                        if row_end <= event_begin and row_end <= end_date:
                            rows[row_index] = event_end
                            found = True
                            break
                        row_index = row_index + 1
                    if not found:
                        rows.append(event_end)
                    event["row_index"] = row_index + 1
                user["max_rows"] = len(rows)

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
