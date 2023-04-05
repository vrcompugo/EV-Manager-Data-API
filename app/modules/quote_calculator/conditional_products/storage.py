import json
import math
from app.modules.external.bitrix24.products import get_product


def add_product(data):
    size = 0
    if data["data"].get("power_usage") not in [None, "", 0, "0"]:
        size = size + math.ceil(float(data["data"].get("power_usage")) / 2500) * 2.5
    if data["data"].get("heater_usage") not in [None, "", 0, "0"]:
        size = size + math.ceil(float(data["data"].get("heater_usage")) / 6100) * 2.5
    is_overwrite = False
    if "overwrite_storage_size" in data["data"] and int(data["data"]["overwrite_storage_size"]) > 0:
        size = int(data["data"]["overwrite_storage_size"])
        is_overwrite = True
    if "overwrite_storage_size" in data["data"] and str(data["data"]["overwrite_storage_size"]) in ["5", "7.5", "10"]:
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
        product["quantity"] = math.ceil((stack_count + 1) / 4)
        data["products"].append(product)
    else:
        if not is_overwrite:
            size = 0
            if data["data"].get("power_usage") not in [None, "", 0, "0"]:
                size = size + math.ceil(float(data["data"].get("power_usage")) / 4200) * 4.2
            if data["data"].get("heater_usage") not in [None, "", 0, "0"]:
                size = size + math.ceil(float(data["data"].get("heater_usage")) / 9000) * 4.2
            full_usage = 0
            if data["data"].get("power_usage") not in [None, "", 0, "0"]:
                full_usage = full_usage + float(data["data"].get("power_usage"))
            if data["data"].get("heater_usage") not in [None, "", 0, "0"]:
                full_usage = full_usage + float(data["data"].get("heater_usage"))
            size = 0
            if 0 < full_usage <= 8000:
                size = 8.4
            if 8000 < full_usage <= 12300:
                size = 12.6
            if 12300 < full_usage <= 16600:
                size = 16.8
            if 16600 < full_usage <= 21000:
                size = 21
            if 21000 < full_usage:
                size = 25.2
            if 26000 < full_usage:
                raise Exception("storage produkt could not be calculated")
        if "solaredge" not in data["data"]["extra_options"]:
            version = "SENEC Home 4 Hybrid"
            product = get_product(label="SENEC Home 4 Hybrid (Gehäuse)", category="Stromspeicher")
        else:
            version = "SENEC Home 4 AC"
            product = get_product(label="SENEC Home 4 AC (Gehäuse)", category="Stromspeicher")
        product["quantity"] = 1
        stack_count = math.ceil(size / 4.2)
        stack = get_product(label="SENEC Home 4 Batteriemodul 4,2 kW", category="Stromspeicher")
        product["NAME"] = f"{version} {round(stack_count * 4.2, 1)} kWh"
        product["PRICE"] = float(product["PRICE"]) * math.ceil(stack_count / 6) + float(stack["PRICE"]) * stack_count
        data["products"].append(product)
        product["storagebox_count"] = math.ceil(stack_count / 6)
        return_product = product
        product = get_product(label="Montage Stromspeicher Home4", category="Stromspeicher")
        product["quantity"] = return_product["storagebox_count"]
        data["products"].append(product)
        product = get_product(label="Home 4 Kit", category="Stromspeicher")
        product["quantity"] = 1
        data["products"].append(product)
        return return_product

    return product
