import json
import math
from app.modules.external.bitrix24.products import get_product


def add_product(data):
    if "storage_size" not in data["calculated"] or data["calculated"]["storage_size"] is None:
        raise Exception("storage produkt could not be calculated")
    version = "SENEC V3 Hybrid"
    if ("pv_kwp" in data["data"] and data["data"]["pv_kwp"] > 11) or "solaredge" in data["data"]["extra_options"]:
        version = "Senec V2.1 AC"
    print(data["data"]["pv_kwp"])
    stack_count = math.ceil((data["calculated"]["storage_size"] - 2.5) / 2.5)
    product = get_product(label=version, category="Stromspeicher")
    product["quantity"] = 1
    stack = get_product(label=f"{version} Akku Stack", category="Stromspeicher")
    product["NAME"] = f"{version} {stack_count * 2.5 + 2.5} LI"
    product["PRICE"] = float(product["PRICE"]) + float(stack["PRICE"]) * stack_count
    data["products"].append(product)
    return product
