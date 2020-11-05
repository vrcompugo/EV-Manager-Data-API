import traceback

from app.exceptions import ApiException
from app.modules.external.bitrix24.products import get_product
from app.modules.settings import get_settings


def get_bluegen_calculation(data):
    calculated = {
    }
    return calculated


def get_bluegen_products(data):
    config = get_settings(section="external/bitrix24")
    try:
        quantity_bluegen_cell = 1
        if "bluegen_cell_count" in data["data"] and data["data"]["bluegen_cell_count"] is not None and data["data"]["bluegen_cell_count"] != "":
            quantity_bluegen_cell = int(data["data"]["bluegen_cell_count"])

        add_direct_product(
            label="BlueGen Brennstoffzelle",
            category="Brennstoffzelle",
            quantity=quantity_bluegen_cell,
            products=data["bluegen_quote"]["products"]
        )

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
            product["total_price"] = float(product["PRICE"]) * float(product["quantity"])
            data["bluegen_quote"]["subtotal_net"] = data["bluegen_quote"]["subtotal_net"] + product["total_price"]
        else:
            print(product["NAME"])
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
