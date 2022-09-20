import json
from app.models import Order

from .utils import get_data_value


def part02_rechnungsanschrift(wb, excel_layout, deal, contact):
    wb["Neukunden"]["S" + str(wb.current_row)] = deal.get("contract_number")
    wb["Neukunden"]["U" + str(wb.current_row)] = contact.get("company")
    wb["Neukunden"]["X" + str(wb.current_row)] = "Frau" if contact.get("salutation") == "ms" else "Herr"
    wb["Neukunden"]["Y" + str(wb.current_row)] = ""  # title
    wb["Neukunden"]["AA" + str(wb.current_row)] = contact.get("first_name")
    wb["Neukunden"]["AB" + str(wb.current_row)] = contact.get("last_name")
    wb["Neukunden"]["AJ" + str(wb.current_row)] = contact.get("street")
    wb["Neukunden"]["AK" + str(wb.current_row)] = contact.get("street_nb")
    wb["Neukunden"]["AO" + str(wb.current_row)] = contact.get("zip")
    wb["Neukunden"]["AP" + str(wb.current_row)] = contact.get("city")
    if len(contact.get("phone", [])) > 0:
        wb["Neukunden"]["AS" + str(wb.current_row)] = contact.get("phone")[0].get("VALUE", "")
    else:
        wb["Neukunden"]["AS" + str(wb.current_row)] = ""
    wb["Neukunden"]["AW" + str(wb.current_row)] = "versorger@energie360.de"
    return wb
