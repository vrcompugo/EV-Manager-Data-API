from app.models import Order

from .utils import get_data_value


def part03_bankdaten_inhaber(wb, excel_layout, deal, contact):
    if excel_layout in ["gas", "power"]:
        wb["Neukunden"]["BR" + str(wb.current_row)] = contact.get("company")
        wb["Neukunden"]["BU" + str(wb.current_row)] = "Frau" if contact.get("salutation") == "ms" else "Herr"
        wb["Neukunden"]["BW" + str(wb.current_row)] = ""  # title
        wb["Neukunden"]["BX" + str(wb.current_row)] = contact.get("first_name")
        wb["Neukunden"]["BY" + str(wb.current_row)] = contact.get("last_name")
        wb["Neukunden"]["BZ" + str(wb.current_row)] = contact.get("street")
        wb["Neukunden"]["CA" + str(wb.current_row)] = contact.get("street_nb")
        wb["Neukunden"]["CE" + str(wb.current_row)] = contact.get("zip")
        wb["Neukunden"]["CF" + str(wb.current_row)] = contact.get("city")
