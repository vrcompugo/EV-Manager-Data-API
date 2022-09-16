import json
import re
import datetime
import traceback

from app.modules.reseller.models.reseller import Reseller, ResellerSchema
from app.modules.cloud.services.calculation import calculate_cloud as get_cloud_calculation
from app.modules.importer.sources.bitrix24._association import find_association
from app.modules.external.bitrix24.lead import get_lead
from app.modules.external.bitrix24.deal import get_deal, get_deals
from app.modules.external.bitrix24.user import get_user
from app.modules.external.bitrix24.products import get_list as get_product_list, get_product
from app.modules.external.bitrix24.contact import get_contact
from app.modules.settings import get_settings
from app.modules.loan_calculation import loan_calculation
from app.utils.jinja_filters import currencyformat

from .conditional_products.pvmodule import add_product as add_product_pv_module
from .conditional_products.storage import add_product as add_product_storage

from .heating_quote import get_heating_calculation, get_heating_products
from .bluegen_quote import get_bluegen_calculation, get_bluegen_calculation2, get_bluegen_products
from .roof_reconstruction_quote import get_roof_reconstruction_calculation, get_roof_reconstruction_products
from .commission import calculate_commission_data


def calculate_quote(lead_id, data=None, create_quote=False):
    module_type_options = []
    config = get_settings(section="external/bitrix24")
    categories = config["product"]["categories"]
    products = get_product_list()
    default_module_type = None
    for product in products:
        if str(product["SECTION_ID"]) == str(categories["PV Module"]):
            if default_module_type is None and product["NAME"].find("SENEC.SOLAR 380 Watt") > 0:
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
    if lead_data["source_id"] == "23":
        deal_datas = get_deals({
            "FILTER[UF_CRM_5FA43F983EBAB]": lead_data["unique_identifier"],
            "FILTER[CATEGORY_ID]": "170"
        })
        if deal_datas is not None and len(deal_datas) > 0:
            lead_data["assigned_by_id"] = deal_datas[0]["assigned_by_id"]
    return_data = {
        "id": lead_id,
        "assigned_by_id": lead_data["assigned_by_id"],
        "assigned_user": None,
        "datetime": str(datetime.datetime.now()),
        "data": {
            "status_id": lead_data.get("status_id"),
            "emove_tarif": "none",
            "bluegen_cell_count": 1,
            "price_increase_rate": 5.75,
            "inflation_rate": 1.75,
            "runtime": 30,
            "financing_rate": 3.75,
            "module_type": default_module_type,
            "investment_type": "financing",
            "price_guarantee": "12_years",
            "roof_direction": "west_east",
            "module_type": default_module_type,
            "roofs": [{
                "direction": "west_east"
            }],
            "consumers": [],
            "extra_options": ["technik_service_packet", "solaredge"],
            "extra_options_zero": [],
            "reconstruction_extra_options": [],
            "heating_quote_extra_options": ["renewable_ready", "multistorage_freshwater"],
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
        "pdf_wi_short_link": "",
        "pdf_datasheet_link": "",
        "is_sent": "",
        "foreword": "",
        "appendix": "",
        "roof_reconstruction_quote": {
            "calculated": {},
            "products": [],
            "has_special_condition": True
        },
        "heating_quote": {
            "calculated": {},
            "products": [],
            "has_special_condition": True
        },
        "bluegen_quote": {
            "calculated": {},
            "products": [],
            "has_special_condition": True
        },
        "products": [],
        "contact": lead_data["contact"],
        "has_special_condition": True,
        "construction_week": "",
        "construction_year": ""
    }
    if data is not None and data.get("special_conditions_pv_quote") in [None, ""] and data.get("special_conditions_heating_quote") in [None, ""] and data.get("special_conditions_roof_reconstruction_quote") in [None, ""]:
        return_data["has_special_condition"] = False
        return_data["roof_reconstruction_quote"]["has_special_condition"] = False
        return_data["heating_quote"]["has_special_condition"] = False
        return_data["bluegen_quote"]["has_special_condition"] = False
        if data.get("has_roof_reconstruction_quote") is True:
            delivery_date = datetime.datetime.now() + datetime.timedelta(weeks=14)
        elif data.get("has_heating_quote") is True:
            delivery_date = datetime.datetime.now() + datetime.timedelta(weeks=16)
        else:
            delivery_date = datetime.datetime.now() + datetime.timedelta(weeks=14)
        return_data["construction_week"] = int(delivery_date.strftime("%U"))
        return_data["construction_year"] = int(delivery_date.strftime("%Y"))
    if lead_data["assigned_by_id"] is not None and lead_data["assigned_by_id"] != "":
        return_data["assigned_user"] = get_user(lead_data["assigned_by_id"])
    reseller_link = find_association("Reseller", remote_id=lead_data["assigned_by_id"])
    if reseller_link is not None:
        schema = ResellerSchema()
        reseller = Reseller.query.get(reseller_link.local_id)
        return_data["reseller"] = schema.dump(reseller, many=False)
    if data is not None:
        return_data["data"] = data
        return_data["commission_total_value"] = 0
        if "has_pv_quote" in data and data["has_pv_quote"]:
            if return_data.get("assigned_user") not in [None, ""]:
                data["assigned_user"] = return_data.get("assigned_user")
                if 330 in return_data["assigned_user"]["UF_DEPARTMENT"] or "330" in return_data["assigned_user"]["UF_DEPARTMENT"]:
                    return_data["data"]["price_guarantee"] = "2_years"
                    data["price_guarantee"] = "2_years"
            calculated = get_cloud_calculation(data)
            return_data["calculated"] = calculated
            return_data = calculate_products(return_data)
            if "commission_value" in return_data["calculated"]:
                return_data["commission_total_value"] = return_data["commission_total_value"] + return_data["calculated"]["commission_value"]
        if "has_roof_reconstruction_quote" in data and data["has_roof_reconstruction_quote"]:
            return_data["roof_reconstruction_quote"]["calculated"] = get_roof_reconstruction_calculation(return_data)
            return_data = get_roof_reconstruction_products(return_data)
            if "commission_value" in return_data["roof_reconstruction_quote"]["calculated"]:
                return_data["commission_total_value"] = return_data["commission_total_value"] + return_data["roof_reconstruction_quote"]["calculated"]["commission_value"]
        if "has_heating_quote" in data and data["has_heating_quote"]:
            return_data["heating_quote"]["calculated"] = get_heating_calculation(return_data)
            return_data = get_heating_products(return_data)
            if "commission_value" in return_data["heating_quote"]["calculated"]:
                return_data["commission_total_value"] = return_data["commission_total_value"] + return_data["heating_quote"]["calculated"]["commission_value"]
        if "has_bluegen_quote" in data and data["has_bluegen_quote"]:
            return_data["bluegen_quote"]["calculated"] = get_bluegen_calculation(return_data)
            return_data = get_bluegen_products(return_data)
            return_data["bluegen_quote"]["calculated"] = get_bluegen_calculation2(return_data)
            if "commission_value" in return_data["bluegen_quote"]["calculated"]:
                return_data["commission_total_value"] = return_data["commission_total_value"] + return_data["bluegen_quote"]["calculated"]["commission_value"]

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
    kwp_special_roof = kwp_cheap_roof = 0
    kwp_normal_roof = kwp
    if data["data"].get("roofs") not in [None, ""]:
        for roof in data["data"]["roofs"]:
            if roof.get("pv_kwp_used", 0) not in [None, 0] and roof.get("pv_kwp_used", 0) > 0:
                print(roof.get("roof_topping"))
                if roof.get("roof_topping") in ["Schieferdeckung"]:
                    kwp_special_roof = kwp_special_roof + roof.get("pv_kwp_used", 0)
                    kwp_normal_roof = kwp_normal_roof - roof.get("pv_kwp_used", 0)
                if roof.get("roof_topping") in ["Trapezblech"]:
                    kwp_cheap_roof = kwp_cheap_roof + roof.get("pv_kwp_used", 0)
                    kwp_normal_roof = kwp_normal_roof - roof.get("pv_kwp_used", 0)

    if kwp == 0:
        return data
    try:
        add_product_pv_module(data)
        storage_product = add_product_storage(data)
        if data["data"].get("additional_cloud_contract") in [None, "", "0", 0]:
            add_direct_product(
                label="Cloud Fähigkeit",
                category="Stromspeicher",
                quantity=1,
                products=data["products"]
            )
        if storage_product is None:
            add_direct_product(
                label="AC-Installation",
                category="Elektrik",
                quantity=kwp,
                products=data["products"]
            )
        else:
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
            label="Anmeldung beim Netzbetreiber",
            category="Elektrik",
            quantity=1,
            products=data["products"]
        )
        add_direct_product(
            label="Die Inbetriebnahme",
            category="Elektrik",
            quantity=1,
            products=data["products"]
        )
        if data["data"].get("additional_cloud_contract") in [None, "", "0", 0]:
            add_direct_product(
                label="Portal Card mit Loadingfunktion",
                category="Optionen PV Anlage",
                quantity=1,
                products=data["products"]
            )
        if kwp_normal_roof > 0:
            add_direct_product(
                label="Montage DC",
                category="PV Module",
                quantity=kwp_normal_roof,
                products=data["products"]
            )
        if kwp_special_roof > 0:
            add_direct_product(
                label="Montage DC bes. Dacheindeckung",
                category="PV Module",
                quantity=kwp_special_roof,
                products=data["products"]
            )
        if kwp_cheap_roof > 0:
            add_direct_product(
                label="Montage DC Trapez",
                category="PV Module",
                quantity=kwp_cheap_roof,
                products=data["products"]
            )
        add_direct_product(
            label="Planung",
            category="PV Module",
            quantity=1,
            products=data["products"]
        )
        '''add_direct_product(
            label="Planung & Montage",
            category="PV Module",
            quantity=kwp,
            products=data["products"]
        )'''
        if "cloud_price_heatcloud" in data["calculated"] and float(data["calculated"]["cloud_price_heatcloud"]) > 0:
            add_direct_product(
                label="Wärme Cloud Paket",
                category="Elektrik",
                quantity=1,
                products=data["products"]
            )
        if "min_kwp_refresh" in data["calculated"] and int(data["calculated"]["min_kwp_refresh"]) > 0:
            add_direct_product(
                label="Integrierung der Bestand-PV-Anlage in das neue Cloud Konzept",
                category="Extra Pakete",
                quantity=1,
                products=data["products"]
            )
        if "roofs" in data["data"]:
            quantity = 0
            if data["data"].get("roofs")[0].get("traufhohe") not in [None, "", 0]:
                if len(data["data"].get("roofs")) == 1 and float(data["data"].get("roofs")[0].get("traufhohe")) >= 5.85:
                    quantity = 1
            if len(data["data"].get("roofs")) > 1:
                quantity = len(data["data"].get("roofs")) - 1
            if quantity > 0:
                add_direct_product(
                    label="Gerüst Paket",
                    category="Extra Pakete",
                    quantity=1,
                    products=data["products"]
                )
        technik_and_service_produkt = None
        if data["data"].get("additional_cloud_contract") in [None, "", "0", 0] and ("technik_service_packet" in data["data"]["extra_options"] or "technik_service_packet" in data["data"]["extra_options_zero"]):
            quantity = 0
            if "technik_service_packet" in data["data"]["extra_options"]:
                quantity = 1
            if storage_product["NAME"].find("Home 4") > 0:
                technik_and_service_produkt = add_direct_product(
                    label="Service, Technik & Garantie Paket Home4",
                    category="Extra Pakete",
                    quantity=quantity,
                    products=data["products"]
                )
            else:
                technik_and_service_produkt = add_direct_product(
                    label="Service, Technik & Garantie Paket",
                    category="Extra Pakete",
                    quantity=quantity,
                    products=data["products"]
                )
            if "technik_service_packet_autumn_extra2" in data["data"]["extra_options"]:
                product = get_product(label="Service, Technik & Garantie Paket Winter Highlight", category="Extra Pakete")
                if product is not None:
                    product["quantity"] = 1
                    product["PRICE"] = -float(product["PRICE"])
                    data["products"].append(product)
            if "technik_service_packet_spring_extra2" in data["data"]["extra_options"]:
                product = get_product(label="Service, Technik & Garantie Paket Frühlings Highlight", category="Extra Pakete")
                if product is not None:
                    product["quantity"] = 1
                    product["PRICE"] = -float(product["PRICE"])
                    data["products"].append(product)
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
            if data["data"]["extra_options_wwwp_variant"] == "NIBE L":
                add_direct_product(
                    label="Brauchwasser-Wärmepumpe L",
                    category="Extra Pakete",
                    quantity=quantity,
                    products=data["products"]
                )
            if data["data"]["extra_options_wwwp_variant"] == "NIBE XL":
                add_direct_product(
                    label="Brauchwasser-Wärmepumpe XL",
                    category="Extra Pakete",
                    quantity=quantity,
                    products=data["products"]
                )
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
            product_label = "Neuer Zählerschrank"
            if data["data"].get("extra_options_new_power_closet_size") in ["3"]:
                product_label = "Neuer Zählerschrank (3)"
            if data["data"].get("extra_options_new_power_closet_size") in ["4"]:
                product_label = "Neuer Zählerschrank (4)"
            if kwp >= 25:
                product_label = "Neuer Zählerschrank (ZS) Wandler fähig"
            if kwp >= 30:
                product_label = "Neuer Zählerschrank (ZS) Wandler-Schrank"
            add_direct_product(
                label=product_label,
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
            elif storage_product["NAME"].find("Home 4") >= 0:
                add_direct_product(
                    label="Home4 BackUp",
                    category="Stromspeicher",
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
            if "wallbox" in data["data"]["extra_options"] and "wallbox" in data["data"]["extra_options"]:
                quantity = data["data"]["extra_options_wallbox_count"]
            wallbox_type = "Heidelberg ECO Home 11kW"
            if "extra_options_wallbox_variant" in data["data"] and data["data"]["extra_options_wallbox_variant"] == "senec-22kW":
                wallbox_type = "Wallbox SENEC 22kW Pro"
            if "extra_options_wallbox_variant" in data["data"] and data["data"]["extra_options_wallbox_variant"] == "control-11kW":
                wallbox_type = "Heidelberg Energy Control. 11 kW"
            if "extra_options_wallbox_variant" in data["data"] and data["data"]["extra_options_wallbox_variant"] == "senec-pro-11kW":
                wallbox_type = "Wallbox SENEC pro S (11kW)"
            add_direct_product(
                label=wallbox_type,
                category="Extra Pakete",
                quantity=quantity,
                products=data["products"]
            )
        if data["data"].get("additional_cloud_contract") in [None, "", "0", 0]:
            add_direct_product(
                label="Unser Komplettschutz",
                category="Optionen PV Anlage",
                quantity=1,
                products=data["products"]
            )
        else:
            add_direct_product(
                label="Unser Komplettschutz EXTRA",
                category="Optionen PV Anlage",
                quantity=1,
                products=data["products"]
            )
        '''add_direct_product(
            label="E.MW (energie-monitoring-wireless)",
            category="Extra Pakete",
            quantity=1,
            products=data["products"]
        )
        if "emw" in data["data"]["extra_options"] or "emw" in data["data"]["extra_options_zero"]:
            quantity = 0
            if "emw" in data["data"]["extra_options"]:
                quantity = 1
            add_direct_product(
                label="E.MW (energie-monitoring-wireless) upgrade",
                category="Extra Pakete",
                quantity=quantity,
                products=data["products"]
            )
        add_direct_product(
            label="Preisgarantie",
            category="Extra Pakete",
            quantity=1,
            products=data["products"]
        )'''
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
    calculate_commission_data(data, data, quote_key="pv_quote")
    data["total_net"] = data["subtotal_net"]
    data["total_tax"] = data["total_net"] * (config["taxrate"] / 100)
    data["total"] = data["total_net"] + data["total_tax"]
    data["tax_rate"] = config["taxrate"]
    if data.get("data").get("investment_type") == 'financing' and data.get("data").get("financing_bank") in ["energie360"]:
        if data.get("data").get("loan_runtime") in [None, "", "0", 0]:
            data["data"]["loan_runtime"] = 240
        if data.get("data").get("loan_upfront") in [None, "", "0", 0]:
            data["data"]["loan_upfront"] = 0
        data["loan_calculation"] = loan_calculation(data["total_net"], data.get("data")["loan_upfront"], data.get("data")["financing_rate"], data["data"]["loan_runtime"])
    return data


def add_direct_product(label, category, quantity, products):
    product = get_product(label=label, category=category)
    if product is not None:
        product["quantity"] = quantity
        products.append(product)
    return product


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


def calculate_heating_usage(lead_id, post_data):
    if post_data.get("heating_quote_house_build") == 'new_building':
        post_data["old_heating_type"] = 'new'

        if float(post_data.get("heating_quote_sqm")) <= 0 or float(post_data.get("heating_quote_people")) < 0:
            return post_data
        heating_usage = float(post_data.get("heating_quote_sqm")) * 18
        water_heating_usage = float(post_data.get("heating_quote_people")) * 320
        post_data["heating_quote_usage"] = heating_usage + water_heating_usage

        if post_data.get("new_heating_type") == 'hybrid_gas':
            wp_percent = 0.60
            if "bufferstorage" in post_data.get("heating_quote_extra_options"):
                wp_percent = 0.75
            post_data["heating_quote_usage_gas"] = round(post_data.get("heating_quote_usage") * (1 - wp_percent))
            post_data["heating_quote_usage_wp"] = round(post_data.get("heating_quote_usage") * wp_percent)
        return post_data
    new_heating_benefit = 0.75
    if post_data.get("heating_quote_old_heating_build") == '2-6_years':
        new_heating_benefit = 0.86
    if post_data.get("heating_quote_old_heating_build") == 'older':
        new_heating_benefit = 0.69
    if post_data.get("new_heating_type") == 'heatpump':
        post_data["heating_quote_usage_gas"] = 0
        post_data["heating_quote_usage_wp"] = (float(post_data.get("heating_quote_usage_old")) * new_heating_benefit) / 3.75
        post_data["heating_quote_usage"] = post_data.get("heating_quote_usage_wp")

    if post_data.get("old_heating_type") == 'heatpump' and post_data.get("new_heating_type") == 'heatpump':
        post_data["heating_quote_usage_gas"] = 0
        post_data["heating_quote_usage_wp"] = (post_data.get("heating_quote_usage_old") * new_heating_benefit)
        post_data["heating_quote_usage"] = post_data.get("heating_quote_usage_wp")
    if post_data.get("new_heating_type") == 'hybrid_gas':
        wp_percent = 0.60
        if "bufferstorage" in post_data.get("heating_quote_extra_options"):
            wp_percent = 0.75
        post_data["heating_quote_usage_gas"] = post_data.get("heating_quote_usage_old") * new_heating_benefit * (1 - wp_percent)
        post_data["heating_quote_usage_wp"] = ((post_data.get("heating_quote_usage_old") * 0.75 * wp_percent)) / 3.75
        post_data["heating_quote_usage"] = post_data.get("heating_quote_usage_gas") + post_data.get("heating_quote_usage_wp")
    if post_data.get("new_heating_type") == 'gas':
        post_data["heating_quote_usage_gas"] = post_data.get("heating_quote_usage_old") * new_heating_benefit
        post_data["heating_quote_usage_wp"] = 0
        post_data["heating_quote_usage"] = post_data.get("heating_quote_usage_gas")
    factors = {
        '1940-1969': 1.125,
        '1970-1979': 1.09,
        '1980-1999': 1.06,
        '2000-2015': 1.035,
        '2016 und neuer': 1.015,
        'new_building': 0.95
    }
    extra_factor = 1
    if factors[post_data.get("heating_quote_house_build")]:
        extra_factor = factors[post_data.get("heating_quote_house_build")]
    post_data["heating_quote_usage_wp"] = post_data.get("heating_quote_usage_wp") * extra_factor
    post_data["heating_quote_usage"] = post_data.get("heating_quote_usage") * extra_factor
    post_data["heating_quote_usage_gas"] = round(post_data.get("heating_quote_usage_gas"))
    post_data["heating_quote_usage_wp"] = round(post_data.get("heating_quote_usage_wp"))
    post_data["heating_quote_usage"] = round(post_data.get("heating_quote_usage"))
    return post_data