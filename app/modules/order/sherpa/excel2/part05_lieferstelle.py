from app.models import Order

from .utils import get_data_value


def part05_lieferstelle(wb, excel_layout, deal, contact):
    wb["Neukunden"]["DP" + str(wb.current_row)] = deal.get("delivery_company", "")
    wb["Neukunden"]["DS" + str(wb.current_row)] = deal.get("delivery_first_name")
    wb["Neukunden"]["DT" + str(wb.current_row)] = deal.get("delivery_last_name")
    wb["Neukunden"]["DV" + str(wb.current_row)] = deal.get("delivery_street")
    wb["Neukunden"]["DW" + str(wb.current_row)] = deal.get("delivery_street_nb")
    wb["Neukunden"]["EA" + str(wb.current_row)] = deal.get("delivery_zip")
    wb["Neukunden"]["EB" + str(wb.current_row)] = deal.get("delivery_city")
