from app.models import Order

from .utils import get_data_value


def part03_bankdaten(wb, excel_layout, deal, contact):
    #if excel_layout == "cloud":
    #    wb["Neukunden"]["BF" + str(wb.current_row)] = "Ja"
    if excel_layout in ["gas", "power"]:
        wb["Neukunden"]["BG" + str(wb.current_row)] = deal.get("bankowner")
        wb["Neukunden"]["BH" + str(wb.current_row)] = deal.get("bank")
        wb["Neukunden"]["BI" + str(wb.current_row)] = deal.get("bic")
        wb["Neukunden"]["BJ" + str(wb.current_row)] = deal.get("iban")
        #wb["Neukunden"]["BF" + str(wb.current_row)] = "Nein"
    wb["Neukunden"]["BP" + str(wb.current_row)] = 1
