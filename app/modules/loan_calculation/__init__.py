

from typing_extensions import runtime


def loan_calculation(total_amount, upfront_payment, interest_rate, runtime_in_months):
    total_amount = float(total_amount)
    upfront_payment = float(upfront_payment)
    interest_rate = float(interest_rate)
    runtime_in_months = int(runtime_in_months)
    loan_amount = (total_amount - upfront_payment)
    monthly_loan_payment = (loan_amount * interest_rate / 12 / 100) / (1 - (1 + interest_rate / 12 / 100) ** -runtime_in_months)
    data = {
        "load_amount": loan_amount,
        "loan_amount": loan_amount,
        "upfront_payment": upfront_payment,
        "monthly_payment": round(monthly_loan_payment, 2),
        "monthly_payment_with_tax": round(monthly_loan_payment * 1.19, 2),
        "yearly_payment": round(monthly_loan_payment * 12, 2),
        "total_cost": 0,
        "interest_rate": interest_rate,
        "runtime_in_months": runtime_in_months,
        "runtime_in_years": round(runtime_in_months / 12, 2),
        "interest_cost": 0
    }
    rest_loan = loan_amount
    for n in range(runtime_in_months):
        interest = rest_loan * (interest_rate / 12 / 100)
        data["interest_cost"] = data["interest_cost"] + interest
        rest_loan = rest_loan + interest - data["monthly_payment"]
    data["total_cost"] = data["interest_cost"] + loan_amount
    return data


def loan_calculation_gross(total_amount_gross, upfront_payment, interest_rate, runtime_in_months):
    total_amount_gross = float(total_amount_gross)
    upfront_payment = float(upfront_payment)
    interest_rate = float(interest_rate)
    runtime_in_months = int(runtime_in_months)
    loan_amount = (total_amount_gross - upfront_payment)
    monthly_loan_payment = (loan_amount * interest_rate / 12 / 100) / (1 - (1 + interest_rate / 12 / 100) ** -runtime_in_months)
    data = {
        "load_amount": loan_amount / 1.19,
        "loan_amount": loan_amount / 1.19,
        "upfront_payment": upfront_payment,
        "monthly_payment": round(monthly_loan_payment / 1.19, 2),
        "monthly_payment_with_tax": round(monthly_loan_payment, 2),
        "yearly_payment": round(monthly_loan_payment * 12, 2),
        "total_cost": 0,
        "interest_rate": interest_rate,
        "runtime_in_months": runtime_in_months,
        "runtime_in_years": round(runtime_in_months / 12, 2),
        "interest_cost": 0
    }
    rest_loan = loan_amount
    for n in range(runtime_in_months):
        interest = rest_loan * (interest_rate / 12 / 100)
        data["interest_cost"] = data["interest_cost"] + interest
        rest_loan = rest_loan + interest - data["monthly_payment_with_tax"]
    data["total_cost"] = data["interest_cost"] + loan_amount
    return data