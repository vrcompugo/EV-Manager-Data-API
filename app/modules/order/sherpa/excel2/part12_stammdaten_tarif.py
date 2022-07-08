from app.models import Order

from .utils import get_data_value


def part12_stammdaten_tarif(wb, excel_layout, deal, contact):
    if excel_layout == "cloud":
        wb["Neukunden"]["GM" + str(wb.current_row)] = "Sondertarif"
    if excel_layout == "power":
        wb["Neukunden"]["GM" + str(wb.current_row)] = ""
    if excel_layout == "gas":
        wb["Neukunden"]["GJ" + str(wb.current_row)] = ""
