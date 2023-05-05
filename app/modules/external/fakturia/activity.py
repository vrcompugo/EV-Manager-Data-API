import json
import time

from ._connector import post, put, get


def generate_invoice(contract_number, data):
    contract_data = get(f"/Contracts/{contract_number}")
    old_payment_method = None
    if data["type"] == "DEFAULT_PERFORMANCE" and contract_data.get("paymentMethod") == "BANKTRANSFER":
        contract_data["paymentMethod"] = "SEPA_DEBIT"
        contract_data = put(f"/Contracts/{contract_number}", contract_data)
    print(post(f"/Contracts/{contract_number}/interimBilling?includeInvoices=true&includeCreditNotes=true"))
    time.sleep(2)
    print(post(f"/Contracts/{contract_number}/Activities", data))
    print(post(f"/Contracts/{contract_number}/interimBilling?includeInvoices=true&includeCreditNotes=true"))
    if old_payment_method is not None:
        print(old_payment_method)
        contract_data = get(f"/Contracts/{contract_number}")
        contract_data["paymentMethod"] = old_payment_method
        contract_data = put(f"/Contracts/{contract_number}", contract_data)
