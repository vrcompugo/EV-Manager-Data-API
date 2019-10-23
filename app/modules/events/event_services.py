import datetime
import traceback

from app import db
from app.utils.set_attr_by_dict import set_attr_by_dict

from .models import EventTrigger, EventAction
from .actions.send_email import send_email
from .actions.export_to_source import export_to_source
from .actions.import_from_source import import_from_source
from .actions.count_lead import count_lead
from .actions.test import test


def add_trigger(data):
    new_item = EventTrigger()
    new_item.datetime = datetime.datetime.now()
    new_item.status = "new"
    new_item = set_attr_by_dict(new_item, data, ["id"])
    db.session.add(new_item)
    db.session.commit()
    return new_item


def run_trigger(trigger):
    trigger.status = "pending"
    db.session.commit()
    actions = db.session.query(EventAction).filter(EventAction.triggers.contains([trigger.name])).order_by(
        EventAction.ordering.asc()).all()
    for action in actions:
        try:
            if action.action == "send_email":
                send_email(trigger, action)
            if action.action == "export_to_source":
                export_to_source(trigger, action)
            if action.action == "import_from_source":
                import_from_source(trigger, action)
            if action.action == "count_lead":
                count_lead(trigger, action)
            if action.action == "test":
                test(trigger, action)
        except Exception as e:
            if trigger.error is None:
                trigger.error = ""
            trigger.error = trigger.error + "\n" + traceback.format_exc()
    if trigger.error is None:
        trigger.status = "done"
        #db.session.delete(trigger)
    else:
        trigger.status = "error"
    db.session.commit()


def add_action(data):
    new_item = EventAction()
    new_item = set_attr_by_dict(new_item, data, ["id"])
    db.session.add(new_item)
    db.session.commit()
    return new_item
