from sqlalchemy import or_

from app import db
from app.models import Lead

from ._progress import printProgressBar


def update_commission_values():
    uncounted_leads = db.session.query(Lead)\
        .filter(Lead.counted_at.is_(None))\
        .filter(or_(
            Lead.contact_source == "DAA",
            Lead.contact_source == "DAA/PV",
            Lead.contact_source == "WattFox ",
            Lead.contact_source == "WattFox",
            Lead.contact_source == "Wattfox",
            Lead.contact_source == "Senec Anfrage",
            Lead.contact_source == "Senec",
        ))\
        .all()
    returned_leads = db.session.query(Lead)\
        .filter(Lead.status == "returned")\
        .filter(Lead.returned_at.is_(None))\
        .filter(or_(
            Lead.contact_source == "DAA",
            Lead.contact_source == "DAA/PV",
            Lead.contact_source == "WattFox ",
            Lead.contact_source == "WattFox",
            Lead.contact_source == "Wattfox",
            Lead.contact_source == "Senec Anfrage",
            Lead.contact_source == "Senec",
        ))\
        .all()
    won_leads = db.session.query(Lead)\
        .filter(Lead.status == "won")\
        .filter(Lead.won_at.is_(None))\
        .filter(or_(
            Lead.contact_source == "DAA",
            Lead.contact_source == "DAA/PV",
            Lead.contact_source == "WattFox ",
            Lead.contact_source == "WattFox",
            Lead.contact_source == "Wattfox",
            Lead.contact_source == "Senec Anfrage",
            Lead.contact_source == "Senec",
        ))\
        .all()
    total = len(uncounted_leads) + len(returned_leads) + len(won_leads)
    printProgressBar(0, total, prefix='Progress:', suffix='Complete', length=50)
    i = 0
    for lead in uncounted_leads:
        lead.counted_at = lead.datetime
        db.session.commit()
        printProgressBar(i, total, prefix='Progress:', suffix='Complete', length=50)
        i = i + 1

    for lead in returned_leads:
        lead.returned_at = lead.last_status_update
        db.session.commit()
        printProgressBar(i, total, prefix='Progress:', suffix='Complete', length=50)
        i = i + 1

    for lead in won_leads:
        lead.won_at = lead.last_status_update
        db.session.commit()
        printProgressBar(i, total, prefix='Progress:', suffix='Complete', length=50)
        i = i + 1



