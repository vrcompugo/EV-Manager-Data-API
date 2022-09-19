from app.models import Order

from .utils import get_data_value


def part05_lieferstelle(wb, excel_layout, order: Order):
    wb["Neukunden"]["DR" + str(wb.current_row)] = order.customer.firstname
    wb["Neukunden"]["DS" + str(wb.current_row)] = order.customer.lastname
    wb["Neukunden"]["DT" + str(wb.current_row)] = order.customer.company
    wb["Neukunden"]["DX" + str(wb.current_row)] = order.street
    wb["Neukunden"]["DY" + str(wb.current_row)] = order.street_nb
    wb["Neukunden"]["EC" + str(wb.current_row)] = order.zip
    wb["Neukunden"]["ED" + str(wb.current_row)] = order.city
