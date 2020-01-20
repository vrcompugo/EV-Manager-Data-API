from sqlalchemy import and_

from app.models import Customer
from app.modules.importer.sources.bitrix24.customer import run_export

from ._progress import printProgressBar


def bitrix_export_all_customer():
    customers = Customer.query.filter(
        and_(
            Customer.customer_number.isnot(None),
            Customer.customer_number != ""
        )
    ).all()
    total = len(customers)
    printProgressBar(0, total, prefix='Progress:', suffix='Complete', length=50)
    i = 0
    for customer in customers:
        run_export(local_id=customer.id)
        i = i + 1
        printProgressBar(i, total, prefix='Progress:', suffix='Complete', length=50)
