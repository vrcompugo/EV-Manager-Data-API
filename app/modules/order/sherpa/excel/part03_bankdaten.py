from app.models import Order

from .utils import get_data_value


def part03_bankdaten(wb, excel_layout, order: Order):
    if excel_layout == "cloud":
        wb["Neukunden"]["BQ" + str(wb.current_row)] = "Ja"
    if excel_layout in ["gas", "power"]:
        # TODO
        if get_data_value(["customer_payment_info", "address_as_customer"], data):
            wb["Neukunden"]["BH" + str(wb.current_row)] = \
                get_data_value(["customer", "address", "firstname"], data) + " " + \
                get_data_value(["customer", "address", "lastname"], data)
        else:
            wb["Neukunden"]["BH" + str(wb.current_row)] = \
                get_data_value(["customer_payment_info", "address", "firstname"], data) + " " + \
                get_data_value(["customer_payment_info", "address", "lastname"], data)
        wb["Neukunden"]["BI" + str(wb.current_row)] = get_data_value(["customer_payment_info", "bank"], data)
        wb["Neukunden"]["BJ" + str(wb.current_row)] = get_data_value(["customer_payment_info", "bic"], data)
        wb["Neukunden"]["BK" + str(wb.current_row)] = get_data_value(["customer_payment_info", "iban"], data)
        wb["Neukunden"]["BQ" + str(wb.current_row)] = "Nein"
    wb["Neukunden"]["BR" + str(wb.current_row)] = 1
