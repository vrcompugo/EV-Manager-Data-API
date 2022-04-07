from app.models import Order

from .utils import get_data_value


def part07_marktpartner(wb, excel_layout, deal, contact):
    wb["Neukunden"]["DW" + str(wb.current_row)] = deal.get("energie_delivery_code")
    wb["Neukunden"]["DY" + str(wb.current_row)] = deal.get("netprovider_code")
