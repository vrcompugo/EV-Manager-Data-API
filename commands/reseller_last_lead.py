import datetime

from app import db
from app.models import Reseller, Lead
from app.modules.lead.lead_services import lead_reseller_auto_assignment

from ._progress import printProgressBar


def reseller_last_lead():
    resellers = db.session.query(Reseller).all()

    total = len(resellers)
    printProgressBar(0, total, prefix='Progress:', suffix='Complete', length=50)
    i = 0
    for reseller in resellers:
        last_lead = db.session.query(Lead).filter(Lead.reseller_id == reseller.id).order_by(Lead.datetime.desc()).first()
        if last_lead is not None:
            reseller.last_assigned_lead = last_lead.datetime
            db.session.commit()
        printProgressBar(i, total, prefix='Progress:', suffix='Complete', length=50)
        i = i + 1
