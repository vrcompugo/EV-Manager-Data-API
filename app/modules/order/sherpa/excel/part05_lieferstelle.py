from app.models import Order

from .utils import get_data_value


def part05_lieferstelle(wb, excel_layout, order: Order):
    wb["Neukunden"]["CQ" + str(wb.current_row)] = order.customer.firstname
    wb["Neukunden"]["CR" + str(wb.current_row)] = order.customer.lastname
    wb["Neukunden"]["CS" + str(wb.current_row)] = order.customer.company
    wb["Neukunden"]["CV" + str(wb.current_row)] = order.street
    wb["Neukunden"]["CW" + str(wb.current_row)] = order.street_nb
    wb["Neukunden"]["CY" + str(wb.current_row)] = order.zip
    wb["Neukunden"]["CZ" + str(wb.current_row)] = order.city
