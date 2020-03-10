import time
from sqlalchemy import and_

from app import db
from app.models import Customer, ImportIdAssociation
from app.modules.importer.sources.bitrix24.customer import run_export, find_association, post

from ._progress import printProgressBar


def bitrix_export_all_customer():
    customers = db.session.query(Customer).all()
    total = len(customers)
    # printProgressBar(0, total, prefix='Progress:', suffix='Complete', length=50)
    i = 0
    for customer in customers:
        link = find_association("Customer", local_id=customer.id)
        if link is not None:
            if customer.customer_number is not None and customer.customer_number != "":
                response = post("crm.contact.get", post_data={
                    "id": link.remote_id,
                    "fields[UF_CRM_1572949928]": customer.customer_number
                })
                time.sleep(0.5)
                if "result" in response:
                    if response["result"]["UF_CRM_1572949928"] != customer.customer_number:
                        print("customer: ", customer.id)
                        print(customer.customer_number, "!=", response["result"]["UF_CRM_1572949928"])
                        response = post("crm.contact.update", post_data={
                            "id": link.remote_id,
                            "fields[UF_CRM_1572949928]": customer.customer_number
                        })
                else:
                    print("customer: ", customer.id)
                    print(response)
                    print(customer.customer_number, "!=", "nothing")
        i = i + 1
        # printProgressBar(i, total, prefix='Progress:', suffix='Complete', length=50)
