from app.models import Order

from .utils import get_data_value


def part08_weitere_daten(wb, excel_layout, deal, contact):
    if excel_layout == "cloud":
        wb["Neukunden"]["EB" + str(wb.current_row)] = "CLOUD"
    if excel_layout == "power":
        wb["Neukunden"]["EB" + str(wb.current_row)] = "KORDS"
