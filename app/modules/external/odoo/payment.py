from datetime import datetime
from app.exceptions import ApiException

from ._connector import patch


def get_payments_by_contract(contract_number, period_start_date: datetime, period_end_date: datetime):
    response = patch("/v1/bitrix/of.bitrix.deal.sale/call/_get_paid_amount", post_data={
        "args": [
            {
                "contract": contract_number, "period_start_date": period_start_date.strftime("%Y-%m-%d"), "period_end_date": period_end_date.strftime("%Y-%m-%d")
            }
        ]
    })
    if response is None:
        return None
    if response.get("error_descrip").find("Could not find a subscription with contract number") > -1:
        return None
    if response.get("error_descrip") not in [None]:
        raise ApiException("odoo-error", f"odoo error: {response.get('error_descrip')}", 500)
    return float(response["amount_paid"])

