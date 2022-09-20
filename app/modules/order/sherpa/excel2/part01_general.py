import json
from dateutil.parser import parse
from app.models import Order

from .utils import get_data_value


def part01_general(wb, excel_layout, deal, contact):
    wb["Neukunden"]["A" + str(wb.current_row)] = deal.get("transaction_code")
    if deal.get("wishdate") not in [None, ""]:
        wb["Neukunden"]["D" + str(wb.current_row)] = parse(deal.get("wishdate")).strftime("%d.%m.%Y")
    return wb
