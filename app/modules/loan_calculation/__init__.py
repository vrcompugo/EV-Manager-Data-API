

from app.exceptions import ApiException


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
        "type": "financing",
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


def leasing_calculation(total_amount_net, upfront_payment, runtime_in_months):
    total_amount = float(total_amount_net)
    upfront_payment = float(upfront_payment)
    if upfront_payment > total_amount * 0.3:
        raise ApiException('to_much_upfront', 'Anzahlung mehr als 30% vom Leasingwert', 400)
    rest_value_factor = 5
    runtime_in_months = int(runtime_in_months)
    loan_amount = (total_amount - upfront_payment)
    if loan_amount < 10000:
        raise ApiException('not_enough', 'Leasingwert unter 10.000€ nicht möglich', 400)
    interest_rate = get_leasing_interest_rate(loan_amount, runtime_in_months)
    monthly_loan_payment = loan_amount * interest_rate  / 100
    rest_value = loan_amount * rest_value_factor / 100
    data = {
        "type": "leasing",
        "load_amount": loan_amount,
        "upfront_payment": upfront_payment,
        "monthly_payment": round(monthly_loan_payment, 2),
        "monthly_payment_with_tax": round(monthly_loan_payment * 1.19, 2),
        "yearly_payment": round(monthly_loan_payment * 12, 2),
        "rest_value": round(rest_value, 2),
        "total_cost": 0,
        "interest_rate": interest_rate,
        "runtime_in_months": runtime_in_months,
        "interest_cost": 0,
        "service_fee": 75
    }
    data["total_cost"] = data["monthly_payment"] * runtime_in_months + data["service_fee"]
    return data


def get_leasing_interest_rate(total_amount_net, runtime_in_months):
    if 500 < total_amount_net <= 25000:
        if runtime_in_months == 96:
            return 1.29
        if runtime_in_months == 108:
            return 1.18
        if runtime_in_months == 120:
            return 1.10
    if 25000 < total_amount_net <= 75000:
        if runtime_in_months == 96:
            return 1.26
        if runtime_in_months == 108:
            return 1.16
        if runtime_in_months == 120:
            return 1.08
    if 75000 < total_amount_net <= 150000:
        if runtime_in_months == 96:
            return 1.25
        if runtime_in_months == 108:
            return 1.14
        if runtime_in_months == 120:
            return 1.06
    return 9999