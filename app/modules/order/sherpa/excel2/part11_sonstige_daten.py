from app.models import Order

from .utils import get_data_value


def part11_sonstige_daten(wb, excel_layout, deal, contact):
    if excel_layout in ["cloud", "power"]:
        wb["Neukunden"]["GF" + str(wb.current_row)] = "Haushalt"
        wb["Neukunden"]["GG" + str(wb.current_row)] = "Ja"
        wb["Neukunden"]["GI" + str(wb.current_row)] = 1231
    if excel_layout == "gas":
        wb["Neukunden"]["GC" + str(wb.current_row)] = "SLP"
        wb["Neukunden"]["GD" + str(wb.current_row)] = "Ja"
        wb["Neukunden"]["GF" + str(wb.current_row)] = 1231
