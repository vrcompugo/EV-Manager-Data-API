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

        if "heating_quote_people" not in data["data"] or data["data"]["heating_quote_people"] == "":
            data["data"]["heating_quote_people"] = 1
        else:
            data["data"]["heating_quote_people"] = int(data["data"]["heating_quote_people"])
        data["heating_quote_sqm"] = int(data["data"]["heating_quote_sqm"])
        data["data"]["heating_quote_sqm"] = int(data["data"]["heating_quote_sqm"])
        if data["data"]["new_heating_type"] in ["heatpump", "hybrid_gas"]:
            extra_quantity = 0
            product_name = ""
            if data["data"]["new_heating_type"] == "hybrid_gas":
                if "heating_quote_house_build" in data["data"]:
                    if data["data"]["heating_quote_house_build"] == "1940-1969":
                        data["heating_quote_sqm"] = data["data"]["heating_quote_sqm"] * 2
                    if data["data"]["heating_quote_house_build"] == "1970-1979":
                        data["heating_quote_sqm"] = data["data"]["heating_quote_sqm"] * 1.75
                    if data["data"]["heating_quote_house_build"] == "1980-1999":
                        data["heating_quote_sqm"] = data["data"]["heating_quote_sqm"] * 1.5
                    if data["data"]["heating_quote_house_build"] == "2000-2015":
                        data["heating_quote_sqm"] = data["data"]["heating_quote_sqm"] * 1.25
                add_direct_product(
                    label="Hybrid Gas/Wärmepumpen System",
                    category=f"Online - Heizung - Hybrid Gas",
                    quantity=1,
                    data=data,
                    products=data["heating_quote"]["products"]
                )
            else:
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
                    if 200 < data["data"]["heating_quote_sqm"] <= 300:
                        product_name = "Luft/Wasser-Wärmepumpe (Neubau 300)"
                    if 300 < data["data"]["heating_quote_sqm"]:
                        product_name = "Luft/Wasser-Wärmepumpe (Neubau 400)"
                if 400 < data["data"]["heating_quote_sqm"]:
                    extra_quantity = data["data"]["heating_quote_sqm"] - 400
                add_direct_product(
                    label=product_name,
                    category=f"Online - Heizung - WP",
                    quantity=1,
                    products=data["heating_quote"]["products"]
                )
            if extra_quantity > 0:
                add_direct_product(
                    label="Erweiterung Heizfläche",
                    category=f"Online - Heizung - WP",
                    quantity=extra_quantity,
                    products=data["heating_quote"]["products"]
                )
            add_direct_product(
                label="Beantragung der BAFA Förderung (Bafa)",
                category=f"Online - Heizung - WP",
                quantity=1,
                products=data["heating_quote"]["products"]
            )
            if data["data"]["new_heating_type"] == "hybrid_gas":
                add_direct_product(
                    label="Inbetriebnahme",
                    category=f"Online - Heizung - Hybrid Gas",
                    quantity=1,
                    products=data["heating_quote"]["products"]
                )
            else:
                add_direct_product(
                    label="Inbetriebnahme",
                    category=f"Online - Heizung - WP",
                    quantity=1,
                    products=data["heating_quote"]["products"]
                )
            if "extra_warm_water" in data["data"].get("heating_quote_extra_options", []):
                quantity = 1
                if data["data"].get("heating_quote_extra_options_extra_warm_water_count", 0) not in [0, "", None]:
                    quantity = int(data["data"].get("heating_quote_extra_options_extra_warm_water_count"))

                add_direct_product(
                    label="grössere Warmwasser Anforderung",
                    category=f"Online - Heizung - Extra Optionen - WP",
                    quantity=quantity,
                    products=data["heating_quote"]["products"],
                    data=data["data"]
                )
            add_direct_product(
                label="Hydraulischer Abgleich",
                category=f"Online - Heizung - WP",
                quantity=1,
                products=data["heating_quote"]["products"]
            )
            if "no_drain" in data["data"].get("heating_quote_extra_options", []):
                add_direct_product(
                    label="Kein Ablauf im Raum der WP vorhanden",
                    category=f"Online - Heizung - Extra Optionen - WP",
                    quantity=1,
                    products=data["heating_quote"]["products"]
                )
        else:
            label_type = "Gas"
            if data["data"]["new_heating_type"] == "oil":
                label_type = "Öl"
            if data["data"]["new_heating_type"] == "gas":
                label_type = "Gas"

            data["heating_quote_sqm"] = data["data"]["heating_quote_sqm"]
            if "heating_quote_house_build" in data["data"]:
                if data["data"]["heating_quote_house_build"] == "1940-1969":
                    data["heating_quote_sqm"] = data["data"]["heating_quote_sqm"] * 2
                if data["data"]["heating_quote_house_build"] == "1970-1979":
                    data["heating_quote_sqm"] = data["data"]["heating_quote_sqm"] * 1.75
                if data["data"]["heating_quote_house_build"] == "1980-1999":
                    data["heating_quote_sqm"] = data["data"]["heating_quote_sqm"] * 1.5
                if data["data"]["heating_quote_house_build"] == "2000-2015":
                    data["heating_quote_sqm"] = data["data"]["heating_quote_sqm"] * 1.25

            if data["data"]["new_heating_type"] == "oil":
                add_direct_product(
                    label="Öl Heizung",
                    category=f"Online - Heizung - Öl",
                    quantity=1,
                    products=data["heating_quote"]["products"],
                    data=data
                )
            product_name = "Gasbrennwertheizung"
            if data["data"]["new_heating_type"] == "gas":
                add_direct_product(
                    label=product_name,
                    category=f"Online - Heizung - Gas",
                    quantity=1,
                    products=data["heating_quote"]["products"],
                    data=data
                )

            if data["data"]["new_heating_type"] in ["gas"]:
                people = data["data"].get("heating_quote_people", 1)
                if people in ["", 0, None]:
                    people = 1
                product_name = "Brauchwasserspeicher"
                category_name = "Online - Heizung - Zubehör"
                if "connect_existing_solarthermie" in data["data"].get("heating_quote_extra_options", []) or "new_solarthermie" in data["data"].get("heating_quote_extra_options", []):
                    product_name = "Schichtenspeicher"
                    category_name = "Online - Heizung - Solarthermie"
                    add_direct_product(
                        label=product_name,
                        category=category_name,
                        quantity=1,
                        products=data["heating_quote"]["products"],
                        data=people
                    )
                else:
                    if people > 4:
                        add_direct_product(
                            label=product_name,
                            category=category_name,
                            quantity=1,
                            products=data["heating_quote"]["products"],
                            data=people
                        )

            if "heating_quote_radiator_type" in data["data"] and data["data"]["heating_quote_radiator_type"] == "mixed":
                add_direct_product(
                    label=f"2ter Heizkreis {label_type}",
                    category=f"Online - Heizung - {label_type}",
                    quantity=1,
                    products=data["heating_quote"]["products"]
                )

            add_direct_product(
                label=f"Systemtrenner Auslaufventil {label_type}",
                category=f"Online - Heizung - {label_type}",
                quantity=1,
                products=data["heating_quote"]["products"]
            )

            add_direct_product(
                label=f"Hydraulischer Abgleich {label_type}",
                category=f"Online - Heizung - {label_type}",
                quantity=1,
                products=data["heating_quote"]["products"]
            )
            quantitiy = data["data"].get("heating_quote_radiator_count", "")
            if quantitiy in ["", 0, None]:
                quantitiy = 10
            else:
                quantitiy = int(quantitiy)
            add_direct_product(
                label=f"Hydraulischer Abgleich {label_type} II",
                category=f"Online - Heizung - {label_type}",
                quantity=quantitiy,
                products=data["heating_quote"]["products"]
            )

        if data["data"]["new_heating_type"] in ["gas"]:
            if "renewable_ready" in data["data"].get("heating_quote_extra_options", []):
                add_direct_product(
                    label="Renewable Ready (20% Förderung möglich)",
                    category=f"Online - Heizung - {label_type}",
                    quantity=1,
                    products=data["heating_quote"]["products"]
                )
            if data["data"]["old_heating_type"] not in ["gas", "flat"]:
                add_direct_product(
                    label="Umbau (wenn kein Gas vorhanden)",
                    category=f"Online - Heizung - {label_type}",
                    quantity=1,
                    products=data["heating_quote"]["products"]
                )

        if data["data"]["new_heating_type"] == "hybrid_gas":
            if "multistorage_freshwater" in data["data"].get("heating_quote_extra_options", []):
                add_direct_product(
                    label="Multispeicher mit Frischwasserstation",
                    category=f"Online - Heizung - Hybrid Gas",
                    quantity=1,
                    products=data["heating_quote"]["products"]
                )

        if "outside_chimney" in data["data"].get("heating_quote_extra_options", []):
            quantitiy = data["data"].get("heating_quote_extra_options_extra_outside_chimney_height", "")
            if quantitiy in ["", "0", 0, None]:
                quantitiy = 1
            else:
                quantitiy = int(quantitiy)
                if quantitiy < 0:
                    quantitiy = 1
            add_direct_product(
                label="Aussen-Schornstein",
                category=f"Online - Heizung - Extra Optionen",
                quantity=quantitiy,
                products=data["heating_quote"]["products"]
            )

        if "bufferstorage" in data["data"].get("heating_quote_extra_options", []) or data["heating_quote_sqm"] >= 350:
            add_direct_product(
                label="Heizungspufferspeicher",
                category=f"Online - Heizung - Extra Optionen",
                quantity=1,
                products=data["heating_quote"]["products"]
            )

        if "remove_existing_solarthermie" in data["data"].get("heating_quote_extra_options", []):
            add_direct_product(
                label="vorhandene Solarthermie demontieren",
                category=f"Online - Heizung - Extra Optionen",
                quantity=1,
                products=data["heating_quote"]["products"]
            )

        if "connect_existing_solarthermie" in data["data"].get("heating_quote_extra_options", []):
            add_direct_product(
                label="vorhandene Solarthermie mit einbinden",
                category=f"Online - Heizung - Extra Optionen",
                quantity=1,
                products=data["heating_quote"]["products"]
            )

        if "new_solarthermie" in data["data"].get("heating_quote_extra_options", []):
            label = "Solarthermie Set (10)"
            print(data["data"].get("heating_quote_new_solarthermie_type", ""))
            if str(data["data"].get("heating_quote_new_solarthermie_type", "")) == "11":
                label = "Solarthermie Set (11)"
            add_direct_product(
                label=label,
                category=f"Online - Heizung - Solarthermie",
                quantity=1,
                products=data["heating_quote"]["products"]
            )

        if "deconstruct_old_heater" in data["data"].get("heating_quote_extra_options", []):
            add_direct_product(
                label='Ausbau der "alten" Heizung ohne Tanks',
                category=f"Online - Heizung - Extra Optionen",
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


def add_direct_product(label, category, quantity, products, data=None):
    product = get_product(label=label, category=category, data=data)
    if product is not None:
        product["quantity"] = quantity
        products.append(product)
