import traceback

from app.exceptions import ApiException
from app.modules.external.bitrix24.products import get_product
from app.modules.settings import get_settings


def get_roof_reconstruction_calculation(data):
    calculated = {}
    if "reconstruction_sqm" not in data["data"] or data["data"]["reconstruction_sqm"] is None or data["data"]["reconstruction_sqm"] == "":
        raise ApiException("reconstruction_sqm", "Angabe der zu Fläche fehlt", 400)
    calculated["roof_sqm"] = float(data["data"]["reconstruction_sqm"])
    return calculated


def get_roof_reconstruction_products(data):
    config = get_settings(section="external/bitrix24")
    try:
        if "reconstruction_extra_options" not in data["data"]:
            data["data"]["reconstruction_extra_options"] = []

        product_name = "Dachsanierung Paket"
        if "reconstruction_roof_type" in data["data"] and data["data"]["reconstruction_roof_type"] == "flat":
            product_name = "Flachdachsanierung"
        if "with_insulation" in data["data"]["reconstruction_extra_options"]:
            product_name = product_name + " mit Dämmung"

        add_direct_product(
            label=product_name,
            category=f"Erneuerbare Energie - Dach",
            quantity=data["roof_reconstruction_quote"]["calculated"]["roof_sqm"],
            products=data["roof_reconstruction_quote"]["products"]
        )

        if "with_asbest_removable" in data["data"]["reconstruction_extra_options"]:
            add_direct_product(
                label="Asbestzementplatten abnehmen und entsorgen",
                category=f"Erneuerbare Energie - Dach",
                quantity=data["roof_reconstruction_quote"]["calculated"]["roof_sqm"],
                products=data["roof_reconstruction_quote"]["products"]
            )

    except Exception as e:
        trace_output = traceback.format_exc()
        print(trace_output)
        data["roof_reconstruction_quote"]["products"] = []
        raise e
    data["roof_reconstruction_quote"]["subtotal_net"] = 0
    for product in data["roof_reconstruction_quote"]["products"]:
        if product["PRICE"] is not None:
            if "reseller" in data and "document_style" in data["reseller"]:
                product["PRICE"] = float(product["PRICE"]) * 1.15
            product["total_price"] = float(product["PRICE"]) * float(product["quantity"])
            data["roof_reconstruction_quote"]["subtotal_net"] = data["roof_reconstruction_quote"]["subtotal_net"] + product["total_price"]
        else:
            print(product["NAME"])
    data["roof_reconstruction_quote"]["total_net"] = data["roof_reconstruction_quote"]["subtotal_net"]
    data["roof_reconstruction_quote"]["total_tax"] = data["roof_reconstruction_quote"]["total_net"] * (config["taxrate"] / 100)
    data["roof_reconstruction_quote"]["total"] = data["roof_reconstruction_quote"]["total_net"] + data["roof_reconstruction_quote"]["total_tax"]
    data["roof_reconstruction_quote"]["tax_rate"] = config["taxrate"]
    return data


def add_direct_product(label, category, quantity, products):
    product = get_product(label=label, category=category)
    if product is not None:
        product["quantity"] = quantity
        products.append(product)
