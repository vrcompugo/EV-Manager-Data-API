from app.modules.external.bitrix24.products import get_product


def add_product(data):

    if "module_kwp" in data["data"]:
        try:
            product = get_product(label=data["data"]["module_kwp"]["label"], category="PV Module")
            if "pv_kwp" in data["data"] and data["data"]["pv_kwp"] is not None:
                product["quantity"] = float(data["data"]["pv_kwp"])
            else:
                product["quantity"] = float(data["calculated"]["min_kwp"])
            data["products"].append(product)
        except Exception as e:
            pass
