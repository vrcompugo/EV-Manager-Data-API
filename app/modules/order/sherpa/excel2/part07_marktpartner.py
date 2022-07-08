from app.models import Order

from .utils import get_data_value


def part07_marktpartner(wb, excel_layout, deal, contact):
    if excel_layout in ["cloud", "power"]:
        wb["Neukunden"]["FA" + str(wb.current_row)] = deal.get("energie_delivery_code")
        wb["Neukunden"]["FC" + str(wb.current_row)] = deal.get("netprovider_code")
    if excel_layout in ["gas"]:
        wb["Neukunden"]["EX" + str(wb.current_row)] = deal.get("energie_delivery_code")
        wb["Neukunden"]["EZ" + str(wb.current_row)] = deal.get("netprovider_code")
