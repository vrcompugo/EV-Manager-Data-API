from app.models import Order

from .utils import get_data_value


def part06_zahlerdaten(wb, excel_layout, order: Order):
    if excel_layout == "cloud":
        wb["Neukunden"]["DK" + str(wb.current_row)] = "0,01"
    if excel_layout in ["gas", "power"]:
        wb["Neukunden"]["DK" + str(wb.current_row)] = order.data["UF_CRM_1598445781387"]
    wb["Neukunden"]["DE" + str(wb.current_row)] = order.data["UF_CRM_1585821761"]
    wb["Neukunden"]["DH" + str(wb.current_row)] = order.data["UF_CRM_1597757913754"]
    wb["Neukunden"]["DJ" + str(wb.current_row)] = "SLP"
