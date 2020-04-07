import datetime

from app import db
from app.models import Customer
from app.modules.importer.sources.bitrix24._association import find_association, associate_item
from app.modules.importer.sources.bitrix24.customer import run_export


def customer_export_missing():
    customers = db.session.query(Customer).all()

    for customer in customers:
        link = find_association("Customer", local_id=customer.id)
        if link is None:
            print(customer.id)
            run_export(local_id=customer.id)
            link = find_association("Customer", local_id=customer.id)
            print(link)
