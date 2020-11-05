import json
import re
import datetime
import traceback

from app.modules.cloud.services.calculation import calculate_cloud as get_cloud_calculation
from app.modules.external.bitrix24.lead import get_lead
from app.modules.external.bitrix24.products import get_list as get_product_list, get_product
from app.modules.external.bitrix24.contact import get_contact
from app.modules.settings import get_settings
from app.utils.jinja_filters import currencyformat

from .conditional_products.pvmodule import add_product as add_product_pv_module
from .conditional_products.storage import add_product as add_product_storage

from .heating_quote import get_heating_calculation, get_heating_products
from .bluegen_quote import get_bluegen_calculation, get_bluegen_products
from .roof_reconstruction_quote import get_roof_reconstruction_calculation, get_roof_reconstruction_products


def calculate_quote(lead_id, data=None, create_quote=False):
    module_type_options = []
    config = get_settings(section="external/bitrix24")
    categories = config["product"]["categories"]
    products = get_product_list()
    default_module_type = None
    for product in products:
        if str(product["SECTION_ID"]) == str(categories["PV Module"]):
            if default_module_type is None:
                default_module_type = int(product["ID"])
            if 'kwp' in product:
                module_type_options.append(
                    {
                        'value': int(product["ID"]),
                        'label': product["NAME"],
                        'kWp': product['kwp'],
                        'qm': product['qm']
                    }
                )
    lead_data = get_lead(lead_id)
    return_data = {
        "id": lead_id,
        "assigned_by_id": lead_data["assigned_by_id"],
        "datetime": str(datetime.datetime.now()),
        "data": {
            "emove_tarif": "none",
            "price_increase_rate": 5.75,
            "inflation_rate": 2.5,
            "financing_rate": 3.79,
            "module_type": default_module_type,
            "investment_type": "financing",
            "price_guarantee": "12_years",
            "roof_direction": "west_east",
            "module_type": default_module_type,
            "roofs": [{
                "direction": "west_east"
            }],
            "consumers": [],
            "extra_options": [],
            "extra_options_zero": [],
            "reconstruction_extra_options": [],
            "heating_quote_extra_options": [],
            "extra_offers": [],
            "address": {}
        },
        "calculated": {
            "min_storage_size": 0
        },
        "select_options": {
            "module_type_options": module_type_options
        },
        "pdf_link": "",
        "pdf_quote_link": "",
        "pdf_wi_link": "",
        "pdf_datasheet_link": "",
        "is_sent": "",
        "foreword": "",
        "appendix": "",
        "roof_reconstruction_quote": {
            "calculated": {},
            "products": []
        },
        "heating_quote": {
            "calculated": {},
            "products": []
        },
        "bluegen_quote": {
            "calculated": {},
            "products": []
        },
        "products": [],
        "contact": lead_data["contact"]
    }

    if "contact_id" in lead_data and lead_data["contact_id"] is not None and int(lead_data["contact_id"]):
        return_data["contact"] = get_contact(lead_data["contact_id"])

    if data is not None:
        return_data["data"] = data
        if "has_pv_quote" in data and data["has_pv_quote"]:
            calculated = get_cloud_calculation(data)
            return_data["calculated"] = calculated
            return_data = calculate_products(return_data)
        if "has_roof_reconstruction_quote" in data and data["has_roof_reconstruction_quote"]:
            return_data["roof_reconstruction_quote"]["calculated"] = get_roof_reconstruction_calculation(return_data)
            return_data = get_roof_reconstruction_products(return_data)
        if "has_heating_quote" in data and data["has_heating_quote"]:
            return_data["heating_quote"]["calculated"] = get_heating_calculation(return_data)
            return_data = get_heating_products(return_data)
        if "has_bluegen_quote" in data and data["has_bluegen_quote"]:
            return_data["bluegen_quote"]["calculated"] = get_bluegen_calculation(return_data)
            return_data = get_bluegen_products(return_data)

    return return_data


def calculate_products(data):

    config = get_settings(section="external/bitrix24")
    if "extra_options" not in data["data"]:
        data["data"]["extra_options"] = []
    if "extra_options_zero" not in data["data"]:
        data["data"]["extra_options_zero"] = []
    data["products"] = []
    kwp = 0
    if "pv_kwp" in data["data"] and data["data"]["pv_kwp"] is not None:
        kwp = float(data["data"]["pv_kwp"])
    else:
        if "calculated" in data and "min_kwp" in data["calculated"]:
            kwp = float(data["calculated"]["min_kwp"])
    if kwp == 0:
        return data
    try:
        add_product_pv_module(data)
        storage_product = add_product_storage(data)
        add_direct_product(
            label="Montage Stromspeicher",
            category="Stromspeicher",
            quantity=1,
            products=data["products"]
        )
        add_direct_product(
            label="Cloud Fähigkeit",
            category="Stromspeicher",
            quantity=1,
            products=data["products"]
        )
        add_direct_product(
            label="AC-Installation mit Speicher.",
            category="Elektrik",
            quantity=kwp,
            products=data["products"]
        )
        add_direct_product(
            label="Überspannungschutz",
            category="Elektrik",
            quantity=1,
            products=data["products"]
        )
        add_direct_product(
            label="BlueCard",
            category="Optionen PV Anlage",
            quantity=1,
            products=data["products"]
        )
        add_direct_product(
            label="Planung & Montage",
            category="PV Module",
            quantity=kwp,
            products=data["products"]
        )
        if "technik_service_packet" in data["data"]["extra_options"] or "technik_service_packet" in data["data"]["extra_options_zero"]:
            quantity = 0
            if "technik_service_packet" in data["data"]["extra_options"]:
                quantity = 1
            add_direct_product(
                label="Service, Technik & Garantie Paket",
                category="Extra Pakete",
                quantity=quantity,
                products=data["products"]
            )
        if "tax_consult" in data["data"]["extra_options"] or "tax_consult" in data["data"]["extra_options_zero"]:
            quantity = 0
            if "tax_consult" in data["data"]["extra_options"]:
                quantity = 1
            add_direct_product(
                label="Steuerliche Beratung durch Steuerkanzlei (Partnerunternehmen)",
                category="Optionen PV Anlage",
                quantity=quantity,
                products=data["products"]
            )
        if "emove.zoe" in data["data"]["extra_options"] or "emove.zoe" in data["data"]["extra_options_zero"]:
            quantity = 0
            if "emove.zoe" in data["data"]["extra_options"]:
                quantity = 1
            add_direct_product(
                label="e.move.ZOE",
                category="Extra Pakete",
                quantity=quantity,
                products=data["products"]
            )
        if ("wwwp" in data["data"]["extra_options"] or "wwwp" in data["data"]["extra_options_zero"]) and "extra_options_wwwp_variant" in data["data"]:
            quantity = 0
            if "wwwp" in data["data"]["extra_options"]:
                quantity = 1
            if data["data"]["extra_options_wwwp_variant"] == "ecoSTAR taglio 100":
                add_direct_product(
                    label="Wärmepumpe (100 l) 100",
                    category="Brauchwasserwärmepumpe",
                    quantity=quantity,
                    products=data["products"]
                )
            if data["data"]["extra_options_wwwp_variant"] == "ecoSTAR taglio 180":
                add_direct_product(
                    label="Standard Warmwasserwärmepumpe (ca. 180 l)",
                    category="Brauchwasserwärmepumpe",
                    quantity=quantity,
                    products=data["products"]
                )
            if data["data"]["extra_options_wwwp_variant"] == "ecoSTAR 310 compact":
                add_direct_product(
                    label="Standard Warmwasserwärmepumpe (ca. 200 l)",
                    category="Brauchwasserwärmepumpe",
                    quantity=quantity,
                    products=data["products"]
                )
        if "solaredge" in data["data"]["extra_options"] or "solaredge" in data["data"]["extra_options_zero"]:
            quantity = 0
            if "solaredge" in data["data"]["extra_options"]:
                quantity = kwp
            add_direct_product(
                label="Solar EDGE",
                category="Extra Pakete",
                quantity=quantity,
                products=data["products"]
            )
        if "new_power_closet" in data["data"]["extra_options"] or "new_power_closet" in data["data"]["extra_options_zero"]:
            quantity = 0
            if "new_power_closet" in data["data"]["extra_options"]:
                quantity = 1
            add_direct_product(
                label="Neuer Zählerschrank",
                category="Extra Pakete",
                quantity=quantity,
                products=data["products"]
            )
        if "emergency_power_box" in data["data"]["extra_options"] or "emergency_power_box" in data["data"]["extra_options_zero"]:
            quantity = 0
            if "emergency_power_box" in data["data"]["extra_options"]:
                quantity = 1
            if storage_product["NAME"].find("V3") > 0:
                add_direct_product(
                    label="SENEC Back up Power Pro",
                    category="Extra Pakete",
                    quantity=quantity,
                    products=data["products"]
                )
            else:
                add_direct_product(
                    label="SENEC Back up Power",
                    category="Extra Pakete",
                    quantity=quantity,
                    products=data["products"]
                )
        if "wallbox" in data["data"]["extra_options"] or "wallbox" in data["data"]["extra_options_zero"]:
            if "extra_options_wallbox_count" not in data["data"] or data["data"]["extra_options_wallbox_count"] is None or data["data"]["extra_options_wallbox_count"] == "":
                data["data"]["extra_options_wallbox_count"] = 1
            else:
                data["data"]["extra_options_wallbox_count"] = int(data["data"]["extra_options_wallbox_count"])
            quantity = 0
            if "wallbox" in data["data"]["extra_options"]:
                quantity = data["data"]["extra_options_wallbox_count"]
            if "extra_options_wallbox_variant" in data["data"] and data["data"]["extra_options_wallbox_variant"] == "22kW":
                add_direct_product(
                    label="Wallbox SENEC 22kW",
                    category="Extra Pakete",
                    quantity=data["data"]["extra_options_wallbox_count"],
                    products=data["products"]
                )
            else:
                add_direct_product(
                    label="Wallbox SENEC 11kW",
                    category="Extra Pakete",
                    quantity=data["data"]["extra_options_wallbox_count"],
                    products=data["products"]
                )
        add_direct_product(
            label="Unser Komplettschutz",
            category="Optionen PV Anlage",
            quantity=1,
            products=data["products"]
        )

        if "has_discount" in data["data"] and data["data"]["has_discount"]:
            if "discount_total" in data["data"] and data["data"]["discount_total"] is not None and data["data"]["discount_total"] != "":
                data["products"].append({
                    "NAME": "Nachlass",
                    "DESCRIPTION": f"{currencyformat(data['data']['discount_total'])} Nachlass",
                    "DESCRIPTION_TYPE": "text",
                    "quantity": 1,
                    "PRICE": -float(data["data"]["discount_total"])
                })

    except Exception as e:
        trace_output = traceback.format_exc()
        print(trace_output)
        data["products"] = []
        raise e
    data["subtotal_net"] = 0
    for product in data["products"]:
        if product["PRICE"] is not None:
            product["total_price"] = float(product["PRICE"]) * float(product["quantity"])
            data["subtotal_net"] = data["subtotal_net"] + product["total_price"]
        else:
            print(product["NAME"])
    data["total_net"] = data["subtotal_net"]
    data["total_tax"] = data["total_net"] * (config["taxrate"] / 100)
    data["total"] = data["total_net"] + data["total_tax"]
    data["tax_rate"] = config["taxrate"]
    return data


def add_direct_product(label, category, quantity, products):
    product = get_product(label=label, category=category)
    if product is not None:
        product["quantity"] = quantity
        products.append(product)


def calculate_extra_products(data):

    config = get_settings(section="external/bitrix24")
    data["extra_quotes"] = []
    try:
        add_quote_wwwp(data)
        add_quote_heizstab(data)
        add_quote_wallbox(data)
        add_quote_blackout_box(data)
    except Exception as e:
        trace_output = traceback.format_exc()
        print(trace_output)
        data["extra_quotes"] = []
    return data
