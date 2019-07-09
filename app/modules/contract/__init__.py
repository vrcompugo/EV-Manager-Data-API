


def import_test_data():
    import random
    from datetime import timedelta, datetime as dt
    from barnum import gen_data
    from app import db
    from app.models import Offer
    from .contract_services import add_item, update_item

    statuses = [
        "open", "sent_to_ev", "in_delivery", "missing_documents", "canceled"
    ]

    offers = db.session.query(Offer).filter(Offer.status == "approved").all()
    for offer in offers:
        add_item({
            "offer_id": offer.id,
            "product_id": offer.product_id,
            "customer_id": offer.customer_id,
            "address_id": offer.address_id,
            "payment_account_id": offer.payment_account_id,
            "reseller_id": offer.reseller_id,
            "datetime": offer.datetime + timedelta(days=random.randint(1, 8)),
            "status": statuses[random.randint(0, 3)],
            "data": offer.data,
            "price_definition": offer.price_definition,
            "errors": []
        })

