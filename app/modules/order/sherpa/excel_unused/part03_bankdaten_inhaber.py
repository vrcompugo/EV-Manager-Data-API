from app.models import Order

from .utils import get_data_value


def part03_bankdaten_inhaber(wb, excel_layout, order: Order):
    if excel_layout in ["gas", "power"]:
        wb["Neukunden"]["BI" + str(wb.current_row)] = get_data_value(["customer_payment_info", "address", "salutation"], data)
        wb["Neukunden"]["BJ" + str(wb.current_row)] = get_data_value(["customer_payment_info", "address", "title"], data)
        wb["Neukunden"]["BK" + str(wb.current_row)] = get_data_value(["customer_payment_info", "address", "firstname"], data)
        wb["Neukunden"]["BL" + str(wb.current_row)] = get_data_value(["customer_payment_info", "address", "lastname"], data)
        wb["Neukunden"]["BM" + str(wb.current_row)] = get_data_value(["customer_payment_info", "address", "company"], data)
        wb["Neukunden"]["BO" + str(wb.current_row)] = get_data_value(["customer_payment_info", "address", "street"], data)
        wb["Neukunden"]["BP" + str(wb.current_row)] = get_data_value(["customer_payment_info", "address", "street_nb"], data)
        wb["Neukunden"]["BR" + str(wb.current_row)] = get_data_value(["customer_payment_info", "address", "zip"], data)
        wb["Neukunden"]["BS" + str(wb.current_row)] = get_data_value(["customer_payment_info", "address", "city"], data)
