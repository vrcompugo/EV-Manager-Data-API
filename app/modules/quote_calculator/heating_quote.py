import traceback

from app.exceptions import ApiException
from app.modules.external.bitrix24.products import get_product
from app.modules.settings import get_settings

from .commission import calculate_commission_data


def get_heating_calculation(data):
    calculated = {
        "heater_sqm": 0
    }
    if "heating_quote_sqm" not in data["data"] or data["data"]["heating_quote_sqm"] is None or data["data"]["heating_quote_sqm"] == "":
        raise ApiException("heating_no_sqm", "Angabe der zu beheizenden Fläche fehlt", 400)
    calculated["heater_sqm"] = int(data["data"]["heating_quote_sqm"])
    if "heating_quote_house_build" in data["data"]:
        if data["data"]["heating_quote_house_build"] == "1940-1969":
            calculated["heater_sqm"] = calculated["heater_sqm"] * 2
        if data["data"]["heating_quote_house_build"] == "1970-1979":
            calculated["heater_sqm"] = calculated["heater_sqm"] * 1.75
        if data["data"]["heating_quote_house_build"] == "1980-1999":
            calculated["heater_sqm"] = calculated["heater_sqm"] * 1.5
        if data["data"]["heating_quote_house_build"] == "2000-2015":
            calculated["heater_sqm"] = calculated["heater_sqm"] * 1.25
    return calculated


def get_heating_products(data):
    config = get_settings(section="external/bitrix24")
    try:

        if data["data"]["new_heating_type"] == "heatpump":
            data["data"]["heating_quote_sqm"] = int(data["data"]["heating_quote_sqm"])
            product_name = ""
            if 0 < data["data"]["heating_quote_sqm"] <= 120:
                product_name = "Luft/Wasser-Wärmepumpe (Bestand 120)"
            if 120 < data["data"]["heating_quote_sqm"] <= 200:
                product_name = "Luft/Wasser-Wärmepumpe (Bestand 200)"
            if 200 < data["data"]["heating_quote_sqm"] <= 250:
                product_name = "Luft/Wasser-Wärmepumpe (Bestand 250)"
            if 250 < data["data"]["heating_quote_sqm"]:
                product_name = "Luft/Wasser-Wärmepumpe (Bestand 400)"
            if "heating_quote_house_build" in data["data"] and data["data"]["heating_quote_house_build"] == "2016 und neuer":
                if 0 < data["data"]["heating_quote_sqm"] <= 200:
                    product_name = "Luft/Wasser-Wärmepumpe (Neubau 200)"
                if 200 < data["data"]["heating_quote_sqm"]:
                    product_name = "Luft/Wasser-Wärmepumpe (Neubau 300)"
            add_direct_product(
                label=product_name,
                category=f"online WP (Neu)",
                quantity=1,
                products=data["heating_quote"]["products"]
            )
            add_direct_product(
                label="Inbetriebnahme",
                category=f"online WP (Neu)",
                quantity=1,
                products=data["heating_quote"]["products"]
            )
            add_direct_product(
                label="Hydraulischer Abgleich",
                category=f"online WP (Neu)",
                quantity=1,
                products=data["heating_quote"]["products"]
            )
            add_direct_product(
                label='Ausbau der "alten" Heizung ohne Tanks',
                category=f"online WP (Neu)",
                quantity=0,
                products=data["heating_quote"]["products"]
            )
            add_direct_product(
                label="grössere Warmwasser Anforderung",
                category=f"online WP (Neu)",
                quantity=0,
                products=data["heating_quote"]["products"]
            )
            add_direct_product(
                label="vorhandene Solarthermie mit einbinden",
                category=f"online WP (Neu)",
                quantity=0,
                products=data["heating_quote"]["products"]
            )
            add_direct_product(
                label="Kein Ablauf im Raum der WP vorhanden",
                category=f"online WP (Neu)",
                quantity=0,
                products=data["heating_quote"]["products"]
            )
        else:
            if "person_in_household" not in data["data"] or data["data"]["person_in_household"] == "":
                data["data"]["person_in_household"] = 1
            else:
                data["data"]["person_in_household"] = int(data["data"]["person_in_household"])

            if data["data"]["new_heating_type"] == "oil":
                label_type = "Öl"
            if data["data"]["new_heating_type"] == "gas":
                label_type = "Gas"
            if data["data"]["new_heating_type"] == "heatpump":
                label_type = "WP"

            add_direct_product(
                label=f"AIO Paket",
                category=f"Heizung - {label_type}",
                quantity=1,
                products=data["heating_quote"]["products"]
            )

            if data["data"]["new_heating_type"] == "oil":
                add_direct_product(
                    label="Öl Heizung",
                    category=f"Heizung - {label_type}",
                    quantity=1,
                    products=data["heating_quote"]["products"]
                )

            if data["data"]["new_heating_type"] == "gas":
                product_name = "HANSA Gas"
                if data["data"]["person_in_household"] > 3:
                    product_name = "HANSA Gas Pega"
                add_direct_product(
                    label=product_name,
                    category=f"Heizung - {label_type}",
                    quantity=1,
                    products=data["heating_quote"]["products"]
                )

            if data["data"]["new_heating_type"] == "heatpump":
                data["data"]["heating_quote_sqm"] = int(data["data"]["heating_quote_sqm"])
                if 0 < data["data"]["heating_quote_sqm"] <= 120:
                    product_name = "Luft-Wasser Wärmepumpe Bestand (0-120)"
                if 120 < data["data"]["heating_quote_sqm"] <= 120:
                    product_name = "Luft-Wasser Wärmepumpe Bestand (125-185)"
                if 185 < data["data"]["heating_quote_sqm"] <= 300:
                    product_name = "Luft-Wasser Wärmepumpe Bestand (185-300)"
                if 300 < data["data"]["heating_quote_sqm"]:
                    product_name = "Luft-Wasser Wärmepumpe Bestand (300-500)"
                if "heating_quote_house_build" in data["data"] and data["data"]["heating_quote_house_build"] == "2016 und neuer":
                    if 0 < data["data"]["heating_quote_sqm"] <= 180:
                        product_name = "Neubau Wärmepumpe Komplettpaket (0-180)"
                    if 180 < data["data"]["heating_quote_sqm"]:
                        product_name = "Neubau Wärmepumpe Komplettpaket (181-250)"
                add_direct_product(
                    label=product_name,
                    category=f"Heizung - {label_type}",
                    quantity=1,
                    products=data["heating_quote"]["products"]
                )

            if data["data"]["new_heating_type"] in ["oil", "gas"]:
                product_name = "Brauchwasserspeicher"
                if "heating_quote_extra_options" in data["data"] and "solarthermie" in data["data"]["heating_quote_extra_options"]:
                    product_name = "Schichtenspeicher"
                add_direct_product(
                    label=product_name,
                    category="Heizung - Optionen für Heizung",
                    quantity=1,
                    products=data["heating_quote"]["products"]
                )
            if data["data"]["new_heating_type"] == "heatpump":
                if "heating_quote_extra_options" in data["data"] and "solarthermie" in data["data"]["heating_quote_extra_options"]:
                    add_direct_product(
                        label="Schichtenspeicher",
                        category="Heizung - Optionen für Heizung",
                        quantity=1,
                        products=data["heating_quote"]["products"]
                    )

            if "heating_quote_extra_options" in data["data"] and "solarthermie" in data["data"]["heating_quote_extra_options"]:
                add_direct_product(
                    label="Solarthermie Set (8)",
                    category="Heizung - Solarthermie",
                    quantity=1,
                    products=data["heating_quote"]["products"]
                )

            if "heating_quote_radiator_type" in data["data"] and data["data"]["heating_quote_radiator_type"] == "mixed":
                add_direct_product(
                    label=f"2ter Heizkreis {label_type}",
                    category=f"Heizung - {label_type}",
                    quantity=1,
                    products=data["heating_quote"]["products"]
                )

            add_direct_product(
                label=f"Systemtrenner Auslaufventil {label_type}",
                category=f"Heizung - {label_type}",
                quantity=1,
                products=data["heating_quote"]["products"]
            )

            if data["data"]["new_heating_type"] == "heatpump":
                add_direct_product(
                    label="WP Elektrik",
                    category=f"Heizung - {label_type}",
                    quantity=1,
                    products=data["heating_quote"]["products"]
                )
                add_direct_product(
                    label="WP Inbetriebnahme",
                    category=f"Heizung - {label_type}",
                    quantity=1,
                    products=data["heating_quote"]["products"]
                )
                add_direct_product(
                    label="WP Befestigung",
                    category=f"Heizung - {label_type}",
                    quantity=1,
                    products=data["heating_quote"]["products"]
                )

            add_direct_product(
                label=f"Hydraulischer Abgleich {label_type}",
                category=f"Heizung - {label_type}",
                quantity=1,
                products=data["heating_quote"]["products"]
            )
            add_direct_product(
                label=f"Hydraulischer Abgleich {label_type} II",
                category=f"Heizung - {label_type}",
                quantity=1,
                products=data["heating_quote"]["products"]
            )
    except Exception as e:
        trace_output = traceback.format_exc()
        print(trace_output)
        data["heating_quote"]["products"] = []
        raise e
    data["heating_quote"]["subtotal_net"] = 0
    for product in data["heating_quote"]["products"]:
        if product["PRICE"] is not None:
            if "reseller" in data and "document_style" in data["reseller"] and data["reseller"]["document_style"] is not None and data["reseller"]["document_style"] == "mitte":
                product["PRICE"] = float(product["PRICE"]) * 1.19
            product["total_price"] = float(product["PRICE"]) * float(product["quantity"])
            data["heating_quote"]["subtotal_net"] = data["heating_quote"]["subtotal_net"] + product["total_price"]
        else:
            print(product["NAME"])
    calculate_commission_data(data["heating_quote"], data, quote_key="heating_quote")
    data["heating_quote"]["total_net"] = data["heating_quote"]["subtotal_net"]
    data["heating_quote"]["total_tax"] = data["heating_quote"]["total_net"] * (config["taxrate"] / 100)
    data["heating_quote"]["total"] = data["heating_quote"]["total_net"] + data["heating_quote"]["total_tax"]
    data["heating_quote"]["tax_rate"] = config["taxrate"]
    return data


def add_direct_product(label, category, quantity, products):
    product = get_product(label=label, category=category)
    if product is not None:
        product["quantity"] = quantity
        products.append(product)
