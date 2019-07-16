import datetime

from app import db
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict

from .models.task import Task, TaskSchema


def add_item(data):
    new_item = Task()
    new_item = set_attr_by_dict(new_item, data, ["id"])
    db.session.add(new_item)
    db.session.commit()
    return new_item


def update_item(id, data):
    item = db.session.query(Task).get(id)
    if item is not None:
        item = set_attr_by_dict(item, data, ["id"])
        db.session.commit()
        return item
    else:
        raise ApiException("item_doesnt_exist", "Item doesn't exist.", 409)


def delete_items_except(items, excepted_items):
    for item in items:
        if item not in excepted_items:
            #item.delete()
            pass


def get_items(tree, sort, offset, limit, fields):
    return get_items_by_model(Task, TaskSchema, tree, sort, offset, limit, fields)


def get_one_item(id, fields = None):
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

