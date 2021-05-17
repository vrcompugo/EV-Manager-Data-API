import traceback

from app.exceptions import ApiException
from app.modules.external.bitrix24.products import get_product
from app.modules.settings import get_settings

from .commission import calculate_commission_data


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

        product_name = "Dachsanierung (Dachsteine ohne Dämmung)"
        if "with_insulation" in data["data"]["reconstruction_extra_options"]:
            product_name = "Dachsanierung (Dachsteine mit Dämmung) pro m²"
        if "reconstruction_roof_type" in data["data"] and data["data"]["reconstruction_roof_type"] == "flat":
            product_name = "Flachdachsanierung"
            if "with_insulation" in data["data"]["reconstruction_extra_options"]:
                product_name = "Flachdachsanierung mit Dämmung"

        add_direct_product(
            label=product_name,
            category=f"Dachsanierung online Bogen",
            quantity=data["roof_reconstruction_quote"]["calculated"]["roof_sqm"],
            products=data["roof_reconstruction_quote"]["products"],
            data=data["roof_reconstruction_quote"]["calculated"]
        )

        trash_management_quantity = 0
        if "trash_management" in data["data"]["reconstruction_extra_options"]:
            if data["data"].get("reconstruction_extra_options_trash_management_amount", 0) not in [0, "", None]:
                trash_management_quantity = int(data["data"].get("reconstruction_extra_options_trash_management_amount", 0))
        add_direct_product(
            label="Abfallentsorgung",
            category=f"Dachsanierung online Bogen",
            quantity=trash_management_quantity,
            products=data["roof_reconstruction_quote"]["products"]
        )
        add_direct_product(
            label="Baustellen Einrichtung",
            category=f"Dachsanierung online Bogen",
            quantity=1,
            products=data["roof_reconstruction_quote"]["products"]
        )

        if "remove_snowstop" in data["data"]["reconstruction_extra_options"]:
            quantity = 1
            if data["data"].get("reconstruction_extra_options_extra_remove_snowstop_count", 0) not in [0, "", None]:
                quantity = int(data["data"].get("reconstruction_extra_options_extra_remove_snowstop_count", 0))
            add_direct_product(
                label="Abnehmen des Schneefanges",
                category=f"Dachsanierung online Bogen",
                quantity=quantity,
                products=data["roof_reconstruction_quote"]["products"]
            )

        if "remove_rain_pipe" in data["data"]["reconstruction_extra_options"]:
            quantity = 1
            if data["data"].get("reconstruction_extra_options_extra_remove_rain_pipe_count", 0) not in [0, "", None]:
                quantity = int(data["data"].get("reconstruction_extra_options_extra_remove_rain_pipe_count", 0))
            add_direct_product(
                label="Alte Dachrinne und Fallrohr abnehmen",
                category=f"Dachsanierung online Bogen",
                quantity=quantity,
                products=data["roof_reconstruction_quote"]["products"]
            )

        if "remove_asbest" in data["data"]["reconstruction_extra_options"]:
            add_direct_product(
                label="Asbestzementplatten abnehmen und entsorgen",
                category=f"Dachsanierung online Bogen",
                quantity=data["roof_reconstruction_quote"]["calculated"]["roof_sqm"],
                products=data["roof_reconstruction_quote"]["products"]
            )

        if "remove_exit_window" in data["data"]["reconstruction_extra_options"]:
            quantity = 1
            if data["data"].get("reconstruction_extra_options_extra_remove_exit_window_count", 0) not in [0, "", None]:
                quantity = int(data["data"].get("reconstruction_extra_options_extra_remove_exit_window_count", 0))
            add_direct_product(
                label="Ausstiegsfenster ausbauen und entsorgen",
                category=f"Dachsanierung online Bogen",
                quantity=quantity,
                products=data["roof_reconstruction_quote"]["products"]
            )

        if "remove_chimney" in data["data"]["reconstruction_extra_options"]:
            quantity = 1
            if data["data"].get("reconstruction_extra_options_extra_remove_chimney_count", 0) not in [0, "", None]:
                quantity = int(data["data"].get("reconstruction_extra_options_extra_remove_chimney_count", 0))
            add_direct_product(
                label="Kamin komplett abnehmen und entsorgen",
                category=f"Dachsanierung online Bogen",
                quantity=quantity,
                products=data["roof_reconstruction_quote"]["products"]
            )

        if "new_rain_pipe" in data["data"]["reconstruction_extra_options"]:
            quantity = 1
            if data["data"].get("reconstruction_extra_options_extra_new_rain_pipe_count", 0) not in [0, "", None]:
                quantity = int(data["data"].get("reconstruction_extra_options_extra_new_rain_pipe_count", 0))
            add_direct_product(
                label="Neue Dachrinne aus Zinkblech",
                category=f"Dachsanierung online Bogen",
                quantity=quantity,
                products=data["roof_reconstruction_quote"]["products"]
            )

        if "move_sat" in data["data"]["reconstruction_extra_options"]:
            quantity = 1
            if data["data"].get("reconstruction_extra_options_extra_move_sat_count", 0) not in [0, "", None]:
                quantity = int(data["data"].get("reconstruction_extra_options_extra_move_sat_count", 0))
            add_direct_product(
                label="Sat Anlage Versetzen",
                category=f"Dachsanierung online Bogen",
                quantity=quantity,
                products=data["roof_reconstruction_quote"]["products"]
            )

        if "chimney_reconstruction" in data["data"]["reconstruction_extra_options"]:
            quantity = 1
            if data["data"].get("reconstruction_extra_options_extra_chimney_reconstruction_count", 0) not in [0, "", None]:
                quantity = int(data["data"].get("reconstruction_extra_options_extra_chimney_reconstruction_count", 0))
            add_direct_product(
                label="Schornstein verschiefern",
                category=f"Dachsanierung online Bogen",
                quantity=quantity,
                products=data["roof_reconstruction_quote"]["products"]
            )

        if "remove_window" in data["data"]["reconstruction_extra_options"]:
            quantity = 1
            if data["data"].get("reconstruction_extra_options_extra_remove_window_count", 0) not in [0, "", None]:
                quantity = int(data["data"].get("reconstruction_extra_options_extra_remove_window_count", 0))
            add_direct_product(
                label="Wohndachfenster ausbauen und entsorgen",
                category=f"Dachsanierung online Bogen",
                quantity=quantity,
                products=data["roof_reconstruction_quote"]["products"]
            )

        if "new_window" in data["data"]["reconstruction_extra_options"]:
            quantity = 1
            if data["data"].get("reconstruction_extra_options_extra_new_window_count", 0) not in [0, "", None]:
                quantity = int(data["data"].get("reconstruction_extra_options_extra_new_window_count", 0))
            add_direct_product(
                label="Wohndachfenster einbauen",
                category=f"Dachsanierung online Bogen",
                quantity=quantity,
                products=data["roof_reconstruction_quote"]["products"]
            )

        add_direct_product(
            label="Dacharbeiten zusätzlich",
            category=f"Dachsanierung online Bogen",
            quantity=0,
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
            if "reseller" in data and "document_style" in data["reseller"] and data["reseller"]["document_style"] is not None and data["reseller"]["document_style"] == "mitte":
                product["PRICE"] = float(product["PRICE"]) * 1.19
            product["total_price"] = float(product["PRICE"]) * float(product["quantity"])
            data["roof_reconstruction_quote"]["subtotal_net"] = data["roof_reconstruction_quote"]["subtotal_net"] + product["total_price"]
        else:
            print(product["NAME"])
    calculate_commission_data(data["roof_reconstruction_quote"], data, quote_key="roof_reconstruction_quote")
    data["roof_reconstruction_quote"]["total_net"] = data["roof_reconstruction_quote"]["subtotal_net"]
    data["roof_reconstruction_quote"]["total_tax"] = data["roof_reconstruction_quote"]["total_net"] * (config["taxrate"] / 100)
    data["roof_reconstruction_quote"]["total"] = data["roof_reconstruction_quote"]["total_net"] + data["roof_reconstruction_quote"]["total_tax"]
    data["roof_reconstruction_quote"]["tax_rate"] = config["taxrate"]
    return data


def add_direct_product(label, category, quantity, products, data=None):
    product = get_product(label=label, category=category, data=data)
    if product is not None:
        product["quantity"] = quantity
        products.append(product)
