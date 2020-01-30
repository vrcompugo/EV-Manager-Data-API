from sqlalchemy import and_

from app import db
from app.models import Customer, ImportIdAssociation
from app.modules.importer.sources.bitrix24.customer import run_export, find_association

from ._progress import printProgressBar


def bitrix_export_all_customer():
    customers = db.session.query(Customer)\
        .outerjoin(ImportIdAssociation, Customer.id == ImportIdAssociation.local_id)\
        .all()
    total = len(customers)
    printProgressBar(0, total, prefix='Progress:', suffix='Complete', length=50)
    i = 0
    for customer in customers:
        link = find_association("Customer", local_id=customer.id)
        if link is None:
            run_export(local_id=customer.id)
        i = i + 1
        printProgressBar(i, total, prefix='Progress:', suffix='Complete', length=50)
