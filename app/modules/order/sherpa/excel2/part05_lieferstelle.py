from app.models import Order

from .utils import get_data_value


def part05_lieferstelle(wb, excel_layout, deal, contact):
    wb["Neukunden"]["CQ" + str(wb.current_row)] = deal.get("delivery_first_name")
    wb["Neukunden"]["CR" + str(wb.current_row)] = deal.get("delivery_last_name")
    wb["Neukunden"]["CS" + str(wb.current_row)] = deal.get("delivery_company", "")
    wb["Neukunden"]["CV" + str(wb.current_row)] = deal.get("delivery_street")
    wb["Neukunden"]["CW" + str(wb.current_row)] = deal.get("delivery_street_nb")
    wb["Neukunden"]["CY" + str(wb.current_row)] = deal.get("delivery_zip")
    wb["Neukunden"]["CZ" + str(wb.current_row)] = deal.get("delivery_city")
