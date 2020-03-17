from app.modules.importer.sources.bitrix24.order import run_import
from app.models import Order


def reimport_orders():
    orders = Order.query.all()
    for order in orders:
        run_import(local_id=order.id)
