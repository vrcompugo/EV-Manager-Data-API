import json
import math
from app.modules.external.bitrix24.products import get_product


def add_product(data):
    if "storage_size" not in data["calculated"] or data["calculated"]["storage_size"] is None:
        raise Exception("storage produkt could not be calculated")
    stack_count = math.ceil((data["calculated"]["storage_size"] - 2.5) / 2.5)
    product = get_product(label="Senec V2.1 AC", category="Stromspeicher")
    product["quantity"] = 1
    stack = get_product(label="Senec V2.1 AC  Akku Stack", category="Stromspeicher")
    product["NAME"] = f"Senec V2.1 AC {stack_count * 2.5 + 2.5} LI"
    product["PRICE"] = float(product["PRICE"]) + float(stack["PRICE"]) * stack_count
    data["products"].append(product)
    return product