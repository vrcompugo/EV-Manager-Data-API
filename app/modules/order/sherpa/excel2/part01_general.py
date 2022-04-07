import json
from app.models import Order

from .utils import get_data_value


def part01_general(wb, excel_layout, deal, contact):
    wb["Neukunden"]["A" + str(wb.current_row)] = deal.get("transaction_code")
    return wb
