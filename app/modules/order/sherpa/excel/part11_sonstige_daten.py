from app.models import Order

from .utils import get_data_value


def part11_sonstige_daten(wb, excel_layout, order: Order):
    if excel_layout in ["cloud", "power"]:
        wb["Neukunden"]["FA" + str(wb.current_row)] = "Haushalt"
        wb["Neukunden"]["FB" + str(wb.current_row)] = "Ja"
        wb["Neukunden"]["FD" + str(wb.current_row)] = 1231
    if excel_layout == "gas":
        wb["Neukunden"]["EX" + str(wb.current_row)] = "SLP"
        wb["Neukunden"]["EY" + str(wb.current_row)] = "Ja"
        wb["Neukunden"]["FA" + str(wb.current_row)] = 1231
