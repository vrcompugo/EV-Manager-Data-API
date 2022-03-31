from app.models import Order

from .utils import get_data_value


def part03_bankdaten(wb, excel_layout, deal, contact):
    if excel_layout == "cloud":
        wb["Neukunden"]["BF" + str(wb.current_row)] = "Ja"
    if excel_layout in ["gas", "power"]:
        wb["Neukunden"]["AW" + str(wb.current_row)] = deal.get("bankowner")
        wb["Neukunden"]["AX" + str(wb.current_row)] = deal.get("bank")
        wb["Neukunden"]["AY" + str(wb.current_row)] = deal.get("bic")
        wb["Neukunden"]["AZ" + str(wb.current_row)] = deal.get("iban")
        wb["Neukunden"]["BF" + str(wb.current_row)] = "Nein"
    wb["Neukunden"]["BG" + str(wb.current_row)] = 1
