import datetime

from app import db
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict
from app.models import CalendarEvent
from app.modules.calendar.calendar_services import add_item as event_add, update_item as event_update

from .models.task import Task, TaskSchema


def add_item(data):
    from app.utils.google_geocoding import geocode_address, route_to_address

    new_item = Task()
    new_item = set_attr_by_dict(new_item, data, ["id"])
    if new_item.location is not None and new_item.location != "":
        location = geocode_address(new_item.location)
        if location is not None and "lat" in location:
            new_item.lat = location["lat"]
            new_item.lng = location["lng"]
        route = route_to_address(new_item.location)
        if route is not None:
            new_item.distance_km = route["distance"]
            new_item.travel_time_minutes = route["duration"]
    db.session.add(new_item)
    db.session.commit()
    update_calender_events(new_item)
    return new_item


def update_item(id, data):
    from app.utils.google_geocoding import geocode_address, route_to_address

    item = db.session.query(Task).get(id)
    if item is not None:
        old_location = item.location
        item = set_attr_by_dict(item, data, ["id"])
        if old_location is not None and old_location != "" and item.location is not None and item.location != old_location:
            location = geocode_address(item.location)
            if location is not None and "lat" in location:
                item.lat = location["lat"]
                item.lng = location["lng"]
        if item.distance_km is None and item.location is not None and item.location != "":
            route = route_to_address(item.location)
            if route is not None:
                item.distance_km = route["distance"]
                item.travel_time_minutes = route["duration"]
        db.session.commit()
        update_calender_events(item)
        return item
    else:
        raise ApiException("item_doesnt_exist", "Item doesn't exist.", 409)


def delete_items_except(items, excepted_items):
    for item in items:
        if item not in excepted_items:
            # item.delete()
            pass


def get_items(tree, sort, offset, limit, fields):
    return get_items_by_model(Task, TaskSchema, tree, sort, offset, limit, fields)


def get_one_item(id, fields=None):
    return get_one_item_by_model(Task, TaskSchema, id, fields, [db.subqueryload("role")])


def update_task_list(old_task_list, new_task_list):
    for new_task in new_task_list:
        old_tasks = find_new_task_in_list(old_task_list, new_task)
        for old_task in old_tasks:
            old_task_list.remove(old_task)
        if len(old_tasks) == 0:
            add_item(new_task)
    for old_task in old_task_list:
        db.session.remove(old_task)


def find_new_task_in_list(old_task_list, new_task):
    old_tasks = []
    for old_task in old_task_list:
        if old_task.action == new_task["action"] and \
                old_task.user_id and new_task["user_id"] and\
                old_task.role_id == new_task["role_id"]:
            old_tasks.append(old_task)
    return old_tasks


def update_calender_events(task: Task):
    if task.begin is None or task.end is None:
        return
    events = CalendarEvent.query.filter(CalendarEvent.task_id == task.id).all()
    members_found = []
    event_data = event_data_by_task(task)
    for event in events:
        member = next((member for member in task.members if member.id == event.user_id), None)
        if member is None:
            db.session.delete(event)
            db.session.commit()
        else:
            event_update(event.id, event_data)
            members_found.append(member.id)
    for member in task.members:
        if member.id not in members_found:
            event_data["user_id"] = member.id
            event_add(event_data)


def event_data_by_task(task: Task):
    import copy
    data = copy.copy(task.__dict__)
    data["task_id"] = task.id
    if "_sa_instance_state" in data:
        del data["_sa_instance_state"]
    if "user_id" in data:
        del data["user_id"]
    if "id" in data:
        del data["id"]
    return data
