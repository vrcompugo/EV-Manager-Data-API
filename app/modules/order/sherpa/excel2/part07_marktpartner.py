from app.models import Order

from .utils import get_data_value


def part07_marktpartner(wb, excel_layout, deal, contact):
    if excel_layout in ["gas", "power"]:
        wb["Neukunden"]["DW" + str(wb.current_row)] = deal.get("netprovider_code")
