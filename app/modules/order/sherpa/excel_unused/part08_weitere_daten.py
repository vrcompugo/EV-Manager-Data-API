from app.models import Order

from .utils import get_data_value


def part08_weitere_daten(wb, excel_layout, order: Order):
    if excel_layout == "cloud":
        wb["Neukunden"]["FG" + str(wb.current_row)] = "CLOUD"  # Partner
    if excel_layout == "power":
        wb["Neukunden"]["FG" + str(wb.current_row)] = "KORDS"
