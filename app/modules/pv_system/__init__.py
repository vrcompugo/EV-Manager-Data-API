import random
from datetime import timedelta, datetime as dt

from app import db


def import_test_data():
    from app.models import Survey
    from barnum import gen_data
    from .pv_system_services import add_item, update_item

    statuses = [
        "created", "sent_out", "declined", "approved"
    ]

    surveys = db.session.query(Survey).filter(Survey.offer_status == "open").all()
    for survey in surveys:
        add_item({
        })