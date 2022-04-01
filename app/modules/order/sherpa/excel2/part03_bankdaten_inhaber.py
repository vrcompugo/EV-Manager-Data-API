from app.models import Order

from .utils import get_data_value


def part03_bankdaten_inhaber(wb, excel_layout, deal, contact):
    if excel_layout in ["gas", "power"]:
        wb["Neukunden"]["BI" + str(wb.current_row)] = "Frau" if contact.get("salutation") == "ms" else "Herr"
        wb["Neukunden"]["BJ" + str(wb.current_row)] = ""  # title
        wb["Neukunden"]["BK" + str(wb.current_row)] = contact.get("first_name")
        wb["Neukunden"]["BL" + str(wb.current_row)] = contact.get("last_name")
        wb["Neukunden"]["BM" + str(wb.current_row)] = contact.get("company")
        wb["Neukunden"]["BO" + str(wb.current_row)] = contact.get("street")
        wb["Neukunden"]["BP" + str(wb.current_row)] = contact.get("street_nb")
        wb["Neukunden"]["BR" + str(wb.current_row)] = contact.get("zip")
        wb["Neukunden"]["BS" + str(wb.current_row)] = contact.get("city")
