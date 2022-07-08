from app.models import Order

from .utils import get_data_value


def part06_zahlerdaten(wb, excel_layout, deal, contact):
    if excel_layout == "cloud":
        wb["Neukunden"]["EN" + str(wb.current_row)] = "0,01"
    if excel_layout in ["gas", "power"]:
        wb["Neukunden"]["EN" + str(wb.current_row)] = ""
    wb["Neukunden"]["EH" + str(wb.current_row)] = deal.get("delivery_counter_number")
    wb["Neukunden"]["EK" + str(wb.current_row)] = deal.get("delivery_usage")
    wb["Neukunden"]["EM" + str(wb.current_row)] = "SLP"
