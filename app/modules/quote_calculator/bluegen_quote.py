import json
import traceback

from app.exceptions import ApiException
from app.modules.external.bitrix24.products import get_product
from app.modules.settings import get_settings
from app.modules.loan_calculation import loan_calculation

from .commission import calculate_commission_data


def get_bluegen_calculation(data):
    power_generated = 0
    heat_generated = 0
    gas_usage = 0
    state_aid = 11200
    if data["data"].get("bluegen_cell_count") in ["", None, "0", 0]:
        data["data"]["bluegen_cell_count"] = 1
    else:
        data["data"]["bluegen_cell_count"] = int(data["data"]["bluegen_cell_count"])
    if data["data"]["bluegen_type"] == "bluegen_home":
        gas_usage = 12500
        power_generated = 8700
        heat_generated = 2500
    if data["data"]["bluegen_type"] == "bluegen":
        gas_usage = 22500
        power_generated = 13000
        heat_generated = 6000
    if data["data"]["bluegen_type"] == "electa300":
        gas_usage = 22500
        power_generated = 6000
        heat_generated = 13000
    power_generated = power_generated * data["data"]["bluegen_cell_count"]
    heat_generated = heat_generated * data["data"]["bluegen_cell_count"]
    gas_usage = gas_usage * data["data"]["bluegen_cell_count"]
    state_aid = state_aid * data["data"]["bluegen_cell_count"]
    conventional_gas_usage = gas_usage / 0.75
    calculated = {
        "cell": {
            "price_tomorrow": (gas_usage * 0.1199) / 12,
            "cloud_runtime": 12,
            "maintainance_cost_monthly": round(576 / 12),
            "full_cost_increase_rate": 7.5,
            "state_aid": state_aid
        },
        "lightcloud": {
            "price_today": (power_generated * 0.34) / 12,
            "full_cost_increase_rate": 7.5
        },
        "heatcloud": {
            "price_today": (power_generated * 0.1199) / 12,
            "full_cost_increase_rate": 7.5
        }
    }
    calculated["cell"]["price_half_time"] = calculated["cell"]["price_tomorrow"] * (1 + calculated["cell"]["full_cost_increase_rate"] / 100) ** int(calculated["cell"]["cloud_runtime"] / 2)
    calculated["cell"]["price_full_time"] = calculated["cell"]["price_tomorrow"] * (1 + calculated["cell"]["full_cost_increase_rate"] / 100) ** calculated["cell"]["cloud_runtime"]
    calculated["lightcloud"]["price_half_time"] = calculated["lightcloud"]["price_today"] * (1 + calculated["lightcloud"]["full_cost_increase_rate"] / 100) ** int(calculated["cell"]["cloud_runtime"] / 2)
    calculated["lightcloud"]["price_full_time"] = calculated["lightcloud"]["price_today"] * (1 + calculated["lightcloud"]["full_cost_increase_rate"] / 100) ** calculated["cell"]["cloud_runtime"]
    calculated["heatcloud"]["price_half_time"] = calculated["heatcloud"]["price_today"] * (1 + calculated["heatcloud"]["full_cost_increase_rate"] / 100) ** int(calculated["cell"]["cloud_runtime"] / 2)
    calculated["heatcloud"]["price_full_time"] = calculated["heatcloud"]["price_today"] * (1 + calculated["heatcloud"]["full_cost_increase_rate"] / 100) ** calculated["cell"]["cloud_runtime"]
    calculated["energy"] = {
        "price_today": calculated["lightcloud"]["price_today"] + calculated["heatcloud"]["price_today"],
        "price_half_time": calculated["lightcloud"]["price_half_time"] + calculated["heatcloud"]["price_half_time"],
        "price_full_time": calculated["lightcloud"]["price_full_time"] + calculated["heatcloud"]["price_full_time"],
        "conventional_gas_usage": conventional_gas_usage,
        "max_value": calculated["lightcloud"]["price_full_time"] + calculated["heatcloud"]["price_full_time"],
        "conventional_maintenance_per_year": 636
    }
    return calculated

def get_bluegen_calculation2(data):
    calculated = data["bluegen_quote"]["calculated"]
    calculated["loan_calculation"] = loan_calculation(data["bluegen_quote"]["total_net"] - calculated["cell"]["state_aid"], 0, 2.49, 240)
    print(json.dumps(calculated["loan_calculation"], indent=2))
    return calculated


def get_bluegen_products(data):
    config = get_settings(section="external/bitrix24")
    try:
        quantity_bluegen_cell = 1
        if "bluegen_cell_count" in data["data"] and data["data"]["bluegen_cell_count"] is not None and data["data"]["bluegen_cell_count"] != "":
            quantity_bluegen_cell = int(data["data"]["bluegen_cell_count"])

        if data["data"].get("bluegen_type") == "electa300":
            add_direct_product(
                label="Brennstoffzellenheizung eLecta300",
                category="Brennstoffzelle",
                quantity=quantity_bluegen_cell,
                products=data["bluegen_quote"]["products"]
            )
        else:
            if data["data"].get("bluegen_type") == "bluegen_home":
                add_direct_product(
                    label="BlueGen Home Brennstoffzelle",
                    category="Brennstoffzelle",
                    quantity=quantity_bluegen_cell,
                    products=data["bluegen_quote"]["products"]
                )
            else:
                add_direct_product(
                    label="BlueGen Brennstoffzelle",
                    category="Brennstoffzelle",
                    quantity=quantity_bluegen_cell,
                    products=data["bluegen_quote"]["products"]
                )

        add_direct_product(
            label="Brennstoffzellen Förder-SERVICE",
            category="Brennstoffzelle",
            quantity=1,
            products=data["bluegen_quote"]["products"]
        )
        if data["data"].get("bluegen_type") != "electa300":
            quantity_storage = 0
            if "add_bluegen_storage" in data["data"] and data["data"]["add_bluegen_storage"] is not None and data["data"]["add_bluegen_storage"] is True:
                quantity_storage = 1

            add_direct_product(
                label="Multifunktionsspeicher",
                category="Brennstoffzelle",
                quantity=quantity_storage,
                products=data["bluegen_quote"]["products"]
            )
    except Exception as e:
        trace_output = traceback.format_exc()
        print(trace_output)
        data["bluegen_quote"]["products"] = []
        raise e
    data["bluegen_quote"]["subtotal_net"] = 0
    for product in data["bluegen_quote"]["products"]:
        if product["PRICE"] is not None:
            if "reseller" in data and "document_style" in data["reseller"] and data["reseller"]["document_style"] is not None and data["reseller"]["document_style"] == "mitte":
                product["PRICE"] = float(product["PRICE"]) * 1.19
            product["total_price"] = float(product["PRICE"]) * float(product["quantity"])
            data["bluegen_quote"]["subtotal_net"] = data["bluegen_quote"]["subtotal_net"] + product["total_price"]
        else:
            print(product["NAME"])
    calculate_commission_data(data["bluegen_quote"], data, quote_key="bluegen_quote")
    data["bluegen_quote"]["total_net"] = data["bluegen_quote"]["subtotal_net"]
    data["bluegen_quote"]["total_tax"] = data["bluegen_quote"]["total_net"] * (config["taxrate"] / 100)
    data["bluegen_quote"]["total"] = data["bluegen_quote"]["total_net"] + data["bluegen_quote"]["total_tax"]
    data["bluegen_quote"]["tax_rate"] = config["taxrate"]
    return data


def add_direct_product(label, category, quantity, products):
    product = get_product(label=label, category=category)
    if product is not None:
        product["quantity"] = quantity
        products.append(product)
