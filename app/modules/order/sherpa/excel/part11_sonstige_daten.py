from app.models import Order

from .utils import get_data_value


def part11_sonstige_daten(wb, excel_layout, order: Order):
    if excel_layout in ["cloud", "power"]:
        wb["Neukunden"]["GG" + str(wb.current_row)] = "Haushalt"  # Kategorie bei NN
        wb["Neukunden"]["GH" + str(wb.current_row)] = "Ja"  # Kundengruppe
        wb["Neukunden"]["GJ" + str(wb.current_row)] = 1231  # Abrechnungszeitpunkt
    if excel_layout == "gas":
        wb["Neukunden"]["GG" + str(wb.current_row)] = "SLP"
        wb["Neukunden"]["GH" + str(wb.current_row)] = "Ja"
        wb["Neukunden"]["GJ" + str(wb.current_row)] = 1231
