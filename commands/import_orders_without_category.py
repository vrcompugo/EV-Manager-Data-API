from sqlalchemy import or_

from app import db
from app.models import Order
from app.modules.importer.sources.bitrix24.order import run_import


def import_orders_without_category():
    orders = db.session.query(Order).filter(Order.category == "").all()
    # printProgressBar(0, total, prefix='Progress:', suffix='Complete', length=50)
    for order in orders:
        print("id", order.id)
        run_import(local_id=order.id)
