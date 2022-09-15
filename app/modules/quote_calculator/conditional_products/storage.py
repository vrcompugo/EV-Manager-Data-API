import json
import math
from app.modules.external.bitrix24.products import get_product


def add_product(data):
    if "storage_size" not in data["calculated"] or data["calculated"]["storage_size"] is None:
        raise Exception("storage produkt could not be calculated")
    if data["calculated"]["storage_size"] == 0:
        return None
    size = math.ceil(data["data"]["power_usage"] / 2500) * 2.5
    is_overwrite = False
    if "overwrite_storage_size" in data["data"] and data["data"]["overwrite_storage_size"] != "":
        if int(data["data"]["overwrite_storage_size"]) > size:
            size = int(data["data"]["overwrite_storage_size"])
            is_overwrite = True
    if not is_overwrite or size <= 10 and (size <= 10 or ("solaredge" not in data["data"]["extra_options"] and data["data"]["power_usage"] < 10000)):
        version = "Senec Lithium Speicher"
        stack_count = math.ceil((size - 2.5) / 2.5)
        if stack_count < 1:
            stack_count = 1
        product = get_product(label=version, category="Stromspeicher")
        product["quantity"] = 1
        stack = get_product(label=f"{version} Akku Stack", category="Stromspeicher")
        product["NAME"] = f"{version} {stack_count * 2.5 + 2.5} LI"
        product["PRICE"] = float(product["PRICE"]) + float(stack["PRICE"]) * stack_count
        data["products"].append(product)

        product = get_product(label="Montage Stromspeicher", category="Stromspeicher")
        product["quantity"] = math.ceil(data["calculated"]["storage_size"] / 10)
        data["products"].append(product)
    else:
        if not is_overwrite:
            size = math.ceil(data["data"]["power_usage"] / 4200) * 4.2
        if "solaredge" not in data["data"]["extra_options"]:
            version = "SENEC Home 4 Hybrid"
            product = get_product(label="SENEC Home 4 Hybrid (Gehäuse)", category="Stromspeicher")
        else:
            version = "SENEC Home 4 AC"
            product = get_product(label="SENEC Home 4 AC (Gehäuse)", category="Stromspeicher")
        product["quantity"] = 1
        stack_count = math.ceil(size / 4.2)
        if stack_count < 3:
            stack_count = 3
        stack = get_product(label="SENEC Home 4 Batteriemodul 4,2 kW", category="Stromspeicher")
        product["NAME"] = f"{version} {round(stack_count * 4.2, 1)} kWh"
        product["PRICE"] = float(product["PRICE"]) * math.ceil(stack_count / 6) + float(stack["PRICE"]) * stack_count
        data["products"].append(product)
        product = get_product(label="Montage Stromspeicher Home4", category="Stromspeicher")
        product["quantity"] = 1
        data["products"].append(product)
        product = get_product(label="Home 4 Kit", category="Stromspeicher")
        product["quantity"] = 1
        data["products"].append(product)

    return product
