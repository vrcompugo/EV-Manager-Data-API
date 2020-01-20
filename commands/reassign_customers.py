from app import db
from app.models import Customer, Lead
from app.modules.importer.sources.bitrix24._association import find_association
from app.modules.importer.sources.bitrix24._connector import post

from ._progress import printProgressBar


def reassign_customers():
    customers = db.session.query(Customer).filter(Customer.reseller_id.is_(None)).all()
    total = len(customers)
    printProgressBar(0, total, prefix='Progress:', suffix='Complete', length=50)
    i = 0
    exported = False
    for customer in customers:
        lead = Lead.query.filter(Lead.customer_id == customer.id).first()
        if lead is not None and lead.reseller_id is not None and lead.reseller_id > 0:
            customer.reseller_id = lead.reseller_id
            db.session.commit()
            customer_link = find_association("Customer", local_id=customer.id)
            reseller_link = find_association("Reseller", local_id=customer.reseller_id)
            if customer_link is not None and reseller_link is not None:
                data = {
                    "ID": customer_link.remote_id,
                    "fields[ASSIGNED_BY_ID]": reseller_link.remote_id
                }
                response = post("crm.contact.update", post_data=data)

        printProgressBar(i, total, prefix='Progress:', suffix='Complete', length=50)
        i = i + 1



