from app.models import Order

from .utils import get_data_value


def part02_rechnungsanschrift(wb, excel_layout, order: Order):
    wb["Neukunden"]["S" + str(wb.current_row)] = order.customer.customer_number
    wb["Neukunden"]["U" + str(wb.current_row)] = order.customer.company
    wb["Neukunden"]["Y" + str(wb.current_row)] = order.customer.salutation
    wb["Neukunden"]["AA" + str(wb.current_row)] = order.customer.title
    wb["Neukunden"]["AB" + str(wb.current_row)] = order.customer.firstname
    wb["Neukunden"]["AC" + str(wb.current_row)] = order.customer.lastname
    wb["Neukunden"]["AK" + str(wb.current_row)] = order.street
    wb["Neukunden"]["AL" + str(wb.current_row)] = order.street_nb
    wb["Neukunden"]["AP" + str(wb.current_row)] = order.zip
    wb["Neukunden"]["AQ" + str(wb.current_row)] = order.city
    wb["Neukunden"]["AT" + str(wb.current_row)] = order.customer.phone
    wb["Neukunden"]["AX" + str(wb.current_row)] = "versorger@energie360.de"
    return wb
