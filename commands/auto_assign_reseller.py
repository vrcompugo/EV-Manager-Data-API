import datetime

from app import db
from app.models import Lead
from app.modules.lead.lead_services import lead_reseller_auto_assignment

from ._progress import printProgressBar


def auto_assign_reseller_cmd():
    since = datetime.date(2020,1,11)
    leads = db.session.query(Lead)\
        .filter(Lead.reseller_id.is_(None))\
        .filter(Lead.datetime > since)\
        .all()

    total = len(leads)
    printProgressBar(0, total, prefix='Progress:', suffix='Complete', length=50)
    i = 0
    for lead in leads:
        lead_reseller_auto_assignment(lead)
        printProgressBar(i, total, prefix='Progress:', suffix='Complete', length=50)
        i = i + 1

