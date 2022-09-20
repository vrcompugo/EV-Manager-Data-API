import json
from app.models import Order

from .utils import get_data_value


def part01_general(wb, excel_layout, deal, contact):
    if deal.get("wishdate") not in [None, ""]:
        wb["Neukunden"]["D" + str(wb.current_row)] = deal.get("wishdate")
    return wb
