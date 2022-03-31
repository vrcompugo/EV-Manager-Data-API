from app.models import Order

from .utils import get_data_value


def part06_zahlerdaten(wb, excel_layout, deal, contact):
    if excel_layout == "cloud":
        wb["Neukunden"]["DK" + str(wb.current_row)] = "0,01"
    if excel_layout in ["gas", "power"]:
        wb["Neukunden"]["DK" + str(wb.current_row)] = ""
    wb["Neukunden"]["DE" + str(wb.current_row)] = deal.get("delivery_counter_number")
    wb["Neukunden"]["DH" + str(wb.current_row)] = deal.get("delivery_usage")
    wb["Neukunden"]["DJ" + str(wb.current_row)] = "SLP"
