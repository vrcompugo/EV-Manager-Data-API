from app import db

from .models.event_trigger import EventTrigger
from .event_services import run_trigger


def cron():
    triggers = db.session.query(EventTrigger).filter(EventTrigger.status == "new").order_by(EventTrigger.id.asc()).all()
    for trigger in triggers:
        run_trigger(trigger)
