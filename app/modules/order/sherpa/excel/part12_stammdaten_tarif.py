from app.models import Order

from .utils import get_data_value


def part12_stammdaten_tarif(wb, excel_layout, order: Order):
    if excel_layout == "cloud":
        wb["Neukunden"]["FH" + str(wb.current_row)] = "Sondertarif"
    if excel_layout == "gas":
        wb["Neukunden"]["FE" + str(wb.current_row)] = get_data_value(["tarif"], counter)
    if excel_layout == "power":
        wb["Neukunden"]["FH" + str(wb.current_row)] = get_data_value(["tarif"], counter)
