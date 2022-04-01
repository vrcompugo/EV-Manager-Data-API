import json
from app.models import Order

from .utils import get_data_value


def part02_rechnungsanschrift(wb, excel_layout, deal, contact):
    wb["Neukunden"]["S" + str(wb.current_row)] = contact.get("fakturia_number")
    wb["Neukunden"]["U" + str(wb.current_row)] = contact.get("company")
    wb["Neukunden"]["X" + str(wb.current_row)] = "Frau" if contact.get("salutation") == "ms" else "Herr"
    wb["Neukunden"]["Y" + str(wb.current_row)] = ""  # title
    wb["Neukunden"]["Z" + str(wb.current_row)] = contact.get("first_name")
    wb["Neukunden"]["AA" + str(wb.current_row)] = contact.get("last_name")
    wb["Neukunden"]["AH" + str(wb.current_row)] = contact.get("street")
    wb["Neukunden"]["AI" + str(wb.current_row)] = contact.get("street_nb")
    wb["Neukunden"]["AK" + str(wb.current_row)] = contact.get("zip")
    wb["Neukunden"]["AL" + str(wb.current_row)] = contact.get("city")
    if len(contact.get("phone", [])) > 0:
        wb["Neukunden"]["AN" + str(wb.current_row)] = contact.get("phone")[0].get("VALUE", "")
    else:
        wb["Neukunden"]["AN" + str(wb.current_row)] = ""
    wb["Neukunden"]["AR" + str(wb.current_row)] = "kundenbetreuung@efi-strom.de"
    return wb
