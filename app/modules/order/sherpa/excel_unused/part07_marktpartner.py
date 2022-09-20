from app.models import Order

from .utils import get_data_value


def part07_marktpartner(wb, excel_layout, order: Order):
    if excel_layout in ["gas", "power"]:
        wb["Neukunden"]["FB" + str(row)] = order.data["UF_CRM_1581074754"] # bisheriger Lieferant
