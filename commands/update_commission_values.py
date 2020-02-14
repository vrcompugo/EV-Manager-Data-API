from sqlalchemy import or_

from app import db
from app.models import Order
from app.modules.order.order_services import commission_calulation, update_item

from ._progress import printProgressBar


def update_commission_values():
    orders = db.session.query(Order).all()
    total = len(orders)
    # printProgressBar(0, total, prefix='Progress:', suffix='Complete', length=50)
    i = 0
    for order in orders:
        print("id", order.id)
        order = commission_calulation(order)
        update_item(order.id, {
            "commission_value_net": order.commission_value_net,
            "commissions": order.commissions
        })
        # printProgressBar(i, total, prefix='Progress:', suffix='Complete', length=50)
        i = i + 1
