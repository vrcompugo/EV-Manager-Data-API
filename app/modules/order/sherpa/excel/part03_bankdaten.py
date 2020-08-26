from app.models import Order

from .utils import get_data_value


def part03_bankdaten(wb, excel_layout, order: Order):
    if excel_layout == "cloud":
        wb["Neukunden"]["BF" + str(wb.current_row)] = "Ja"
    if excel_layout in ["gas", "power"]:
        # TODO
        if get_data_value(["customer_payment_info", "address_as_customer"], data):
            wb["Neukunden"]["AW" + str(wb.current_row)] = \
                get_data_value(["customer", "address", "firstname"], data) + " " + \
                get_data_value(["customer", "address", "lastname"], data)
        else:
            wb["Neukunden"]["AW" + str(wb.current_row)] = \
                get_data_value(["customer_payment_info", "address", "firstname"], data) + " " + \
                get_data_value(["customer_payment_info", "address", "lastname"], data)
        wb["Neukunden"]["AX" + str(wb.current_row)] = get_data_value(["customer_payment_info", "bank"], data)
        wb["Neukunden"]["AY" + str(wb.current_row)] = get_data_value(["customer_payment_info", "bic"], data)
        wb["Neukunden"]["AZ" + str(wb.current_row)] = get_data_value(["customer_payment_info", "iban"], data)
        wb["Neukunden"]["BF" + str(wb.current_row)] = "Nein"
    wb["Neukunden"]["BG" + str(wb.current_row)] = 1
