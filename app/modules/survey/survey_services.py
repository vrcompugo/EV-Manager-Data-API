import datetime

from app import db
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict

from .models.survey import Survey, SurveySchema, DATA_STATUSES, OFFER_STATUSES


def add_item(data):
    from app.modules.task.task_services import update_tasks_by_survey
    new_item = Survey()
    new_item = set_attr_by_dict(new_item, data, ["id","offer_status"])
    db.session.add(new_item)
    db.session.commit()
    if new_item.data_status == DATA_STATUSES.COMPLETE:
        update_item(new_item.id, {
            "offer_status": OFFER_STATUSES.OPEN
        })
    else:
        update_tasks_by_survey(new_item)
    return new_item


def update_item(id, data):
    from app.modules.task.task_services import update_tasks_by_survey
    item = db.session.query(Survey).get(id)
    if item is not None:
        updated_item = set_attr_by_dict(item, data, ["id"])
        db.session.commit()
        update_tasks_by_survey(updated_item)
        return item
    else:
        raise ApiException("item_doesnt_exist", "Item doesn't exist.", 409)


def get_items(tree, sort, offset, limit, fields):
    return get_items_by_model(Survey, SurveySchema, tree, sort, offset, limit, fields)


def get_one_item(id, fields = None):
    return get_one_item_by_model(Survey, SurveySchema, id, fields, [db.subqueryload("role")])

