import json
from app.models import Order

from .utils import get_data_value


def part02_rechnungsanschrift(wb, excel_layout, deal, contact):
    from app.modules.cloud.services.contract import normalize_contract_number
    contract_number = normalize_contract_number(deal.get("contract_number"))
    if contract_number == deal.get("contract_number"):
        if deal.get("is_cloud_consumer") in [True, "true", 1, "1"]:
            contract_number = contract_number + "c1"
            if deal.get("title").find(deal.get("contract_number") + "c2") >= 0:
                contract_number = deal.get("contract_number") + "c2"
        if deal.get("is_cloud_heatcloud") in [True, "true", 1, "1"]:
            contract_number = contract_number + "w1"
        if deal.get("is_cloud_ecloud") in [True, "true", 1, "1"]:
            contract_number = contract_number + "ec"
    wb["Neukunden"]["S" + str(wb.current_row)] = contract_number
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
