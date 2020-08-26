from app.models import Order

from .utils import get_data_value


def part02_rechnungsanschrift(wb, excel_layout, order: Order):
    wb["Neukunden"]["S" + str(wb.current_row)] = order.customer.customer_number
    wb["Neukunden"]["U" + str(wb.current_row)] = order.customer.company
    wb["Neukunden"]["X" + str(wb.current_row)] = order.customer.salutation
    wb["Neukunden"]["Y" + str(wb.current_row)] = order.customer.title
    wb["Neukunden"]["Z" + str(wb.current_row)] = order.customer.firstname
    wb["Neukunden"]["AA" + str(wb.current_row)] = order.customer.lastname
    wb["Neukunden"]["AH" + str(wb.current_row)] = order.street
    wb["Neukunden"]["AI" + str(wb.current_row)] = order.street_nb
    wb["Neukunden"]["AK" + str(wb.current_row)] = order.zip
    wb["Neukunden"]["AL" + str(wb.current_row)] = order.city
    wb["Neukunden"]["AN" + str(wb.current_row)] = order.customer.phone
    wb["Neukunden"]["AR" + str(wb.current_row)] = "kundenbetreuung@efi-strom.de"
    return wb
