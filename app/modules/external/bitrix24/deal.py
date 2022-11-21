from enum import unique
import json
import datetime
import math

from sqlalchemy.sql.sqltypes import Date

from app.modules.settings import get_settings, set_settings
from app.modules.external.bitrix24.contact import get_contact
from app.modules.external.bitrix24.user import get_user
from app.utils.dict_func import flatten_dict
from app.modules.quote_calculator.models.quote_history import QuoteHistory

from ._connector import get, post
from ._field_values import convert_field_euro_from_remote, convert_field_select_from_remote


def convert_config_values(data_raw):
    config = get_settings(section="external/bitrix24")
    data = {}
    for key in data_raw.keys():
        if key[:2] == "UF":
            data[key] = data_raw[key]
        else:
            data[key.lower()] = data_raw[key]

    for local_field, external_field in config["deal"]["fields"].items():
        if external_field.lower() in data:
            data[local_field] = data[external_field.lower()]
        if external_field in data:
            data[local_field] = data[external_field]
        if local_field in data and local_field in config["select_lists"]:
            if isinstance(data[local_field], list):
                for index in range(len(data[local_field])):
                    if str(data[local_field][index]) in config["select_lists"][local_field]:
                        data[local_field][index] = config["select_lists"][local_field][str(data[local_field][index])]
            else:
                if data[local_field] in config["select_lists"][local_field]:
                    data[local_field] = config["select_lists"][local_field][data[local_field]]

    return data


def get_deals(payload, force_reload=False):
    payload["start"] = 0
    result = []
    if "SELECT" in payload and payload["SELECT"] == "full":
        del payload["SELECT"]
        config = get_settings(section="external/bitrix24")
        payload["SELECT[0]"] = "*"
        for index, field in enumerate(config["deal"]["fields"]):
            payload[f"SELECT[{index + 1}]"] = config["deal"]["fields"][field]
    while payload["start"] is not None:
        data = post("crm.deal.list", payload, force_reload=force_reload)
        if "result" in data:
            payload["start"] = data["next"] if "next" in data else None
            for item in data["result"]:
                result.append(convert_config_values(item))
        else:
            print("error3:", data)
            payload["start"] = None
            return None
    return result


def get_deals_normalized(filters):
    config = get_settings("external/bitrix24")
    payload = {"SELECT[0]": "*"}
    for field in config["deal"]["fields"].values():
        payload[f"SELECT[{len(payload)}]"] = field
    for filter in filters.keys():
        if filter in config['deal']['fields']:
            payload[f"FILTER[{config['deal']['fields'][filter]}]"] = filters[filter]
        else:
            payload[f"FILTER[{filter.upper()}]"] = filters[filter]
    return get_deals(payload)


def get_deal(id, force_reload=False):
    data = post("crm.deal.get", {
        "ID": id
    }, force_reload=force_reload)
    if "result" in data:
        return convert_config_values(data["result"])
    else:
        print("error deal get:", data)
    return None


def get_deal_products(id):
    data = post("crm.deal.productrows.get", {
        "id": id
    })
    if "result" in data:
        return data["result"]
    else:
        print("error:", data)
    return None


def update_deal_products(id, data, domain=None):
    if "products" not in data:
        return False
    config = get_settings(section="external/bitrix24")
    index = 0
    update_data = {"id": id}
    for product in data["products"]:
        if "price" not in product:
            print(product)
            continue
        product_data = {
            "PRODUCT_NAME": product["label"],
            "ORIGINAL_PRODUCT_NAME": product["label"],
            "PRODUCT_DESCRIPTION": product["description"],
            "PRICE": product["price"],
            "PRICE_EXCLUSIVE": product["price"],
            "PRICE_NETTO": product["price"],
            "PRICE_BRUTTO": product["price"],
            "PRICE_ACCOUNT": product["price"],
            "QUANTITY": product["quantity"],
            "DISCOUNT_TYPE_ID": 2,
            "DISCOUNT_RATE": 0,
            "DISCOUNT_SUM": 0,
            "TAX_RATE": config["taxrate"],
            "TAX_INCLUDED": "N",
            "CUSTOMIZED": "Y",
            "MEASURE_CODE": 796,
            "MEASURE_NAME": "Stück",
            "SORT": 10
        }
        if "id" in product:
            product_data["PRODUCT_ID"] = product["id"]
        for key in product_data.keys():
            update_data[f"rows[{index}][{key.upper()}]"] = product_data[key]
        index = index + 1
    response = post("crm.deal.productrows.set", update_data, domain=domain)
    if "result" in response and response["result"]:
        return True
    else:
        return False


def add_deal(data, domain=None):
    config = get_settings(section="external/bitrix24", domain_raw=domain)
    fields = config["deal"]["fields"]
    update_data = {}
    update_data = flatten_dict(data, update_data, fields=fields, config=config)
    response = post("crm.deal.add", update_data, domain=domain)
    if "result" in response and response["result"]:
        return get_deal(int(response["result"]))
    else:
        return False


def update_deal(id, data, domain=None):
    update_data = {"id": id}
    config = get_settings(section="external/bitrix24", domain_raw=domain)
    fields = config["deal"]["fields"]
    update_data = flatten_dict(data, update_data, fields=fields, config=config)
    response = post("crm.deal.update", update_data, domain=domain)
    if "result" in response and response["result"]:
        return True
    else:
        return False


def run_cron_add_missing_values():
    print("add_missing_deal_values")
    config = get_settings("external/bitrix/add_deals_missing_values")
    if config is None:
        print("no config for add_deals_missing_values")
        return None

    last_import_datetime = datetime.datetime.now()
    payload = {
        "SELECT": "full",
        "filter[CATEGORY_ID]": 0,
        "filter[STAGE_ID]": "NEW",
    }
    if "last_import_datetime" in config:
        payload["filter[>DATE_MODIFY]"] = config["last_import_datetime"]
    deals = get_deals(payload, force_reload=True)
    if deals is not None and len(deals) > 0:
        for deal in deals:
            set_missing_values(deal)

        config = get_settings("external/bitrix/add_deals_missing_values")
        if config is not None:
            config["last_import_datetime"] = last_import_datetime.astimezone().isoformat()
        set_settings("external/bitrix/add_deals_missing_values", config)


def set_missing_values(deal):
    if "unique_identifier" in deal:
        history = QuoteHistory.query.filter(QuoteHistory.lead_id == deal["unique_identifier"]).order_by(QuoteHistory.datetime.desc()).first()
        if history is None:
            return
        update_data = {
            "cloud_type": ["keine Auswahl"],
            "storage_size": ["keine Auswahl"],
            "inverter_type": ["keine Auswahl"],
            "extra_packages": ["keine Auswahl"],
            "extra_packages2": ["keine Auswahl"],
            "quote_type2": [],
            "tax_consultant": "Nein",
            "bwwp": ["keine Auswahl"],
            "pv_module": ["keine Auswahl"],
            "count_modules": 0,
            "emove_packet": "none",
            "hwp": ["keine Auswahl"],
            "expansion_type": "nein",
            "construction_calendar_week_heating": 99,
            "solar_edge_guarantee_extend": "Nein",
            "has_overlandconnection": "nein",
            "storage_model": ["kein Speicher"]
        }
        if history.data["data"].get("has_pv_quote") is True:
            cloud_type = ["Zero"]
            if history.data["calculated"]["min_kwp_ecloud"] > 0:
                cloud_type.append("eCloud")
            if history.data["calculated"]["min_kwp_heatcloud"] > 0:
                cloud_type.append("Wärmecloud")
            if history.data["calculated"]["min_kwp_consumer"] > 0:
                cloud_type.append("Consumer")

            if history.data["data"].get("additional_cloud_contract") in ["true", True, 1] or history.data["data"].get("cloud_quote_type") in ["combination_quote"]:
                if history.data["calculated"]["min_kwp_light"] > 0:
                    update_data["expansion_type"] = "ja, mit zusätzlichen Speicher"
                else:
                    update_data["expansion_type"] = "ja, ohne zusätzlichen Speicher"

            stack_count = math.ceil((history.data["calculated"]["storage_size"] - 2.5) / 2.5)
            stack_count = stack_count * 2.5 + 2.5
            storage_size = [f"Senec {stack_count} Li"]

            update_data["storage_model"] = ["muss projektiert werden"]
            update_data["storage_size"] = storage_size
            home4_ac = next((item for item in history.data["products"] if item["NAME"].find("Home 4 AC") >= 0), None)
            home4_hybrid = next((item for item in history.data["products"] if item["NAME"].find("Home 4 Hybrid") >= 0), None)
            if home4_ac is not None or home4_hybrid is not None:
                if home4_ac is not None:
                    update_data["storage_model"] = ["Senec Home 4 AC"]
                    update_data["storage_size"] = [home4_ac["NAME"].replace(".", ",").replace("Home 4 AC ", "") + " LI"]
                if home4_hybrid is not None:
                    update_data["storage_model"] = ["Senec Home 4 Hybrid"]
                    update_data["storage_size"] = [home4_hybrid["NAME"].replace(".", ",").replace("Home 4 Hybrid ", "") + " LI"]
            update_data["cloud_type"] = cloud_type
            update_data["inverter_type"] = ["Fremdwechselrichter (Fronius bevorzugt) oder 10 Jahre Garantie WR"]
            update_data["extra_packages"] = []
            update_data["extra_packages2"] = []
            update_data["quote_type2"] = []
            update_data["tax_consultant"] = "Nein"
            update_data["bwwp"] = ["keine Auswahl"]
            update_data["pv_module"] = ["keine Auswahl"]
            update_data["count_modules"] = 0
            update_data["emove_packet"] = "none"
            update_data["hwp"] = ["keine Auswahl"]
            update_data["expansion_type"] = "nein"
            if history.data["data"].get("roofs") not in [None, ""]:
                for roof in history.data["data"].get("roofs"):
                    if roof.get("oberleitung_vorhanden") in [True, "true"]:
                        update_data["has_overlandconnection"] = "ja"
                        break

            if "solaredge" in history.data["data"]["extra_options"]:
                update_data["inverter_type"] = ["Solar Edge (Optimierer laut Auslegung)"]
            if "technik_service_packet" in history.data["data"]["extra_options"]:
                update_data["extra_packages"] = ["Technik & Service (Anschlussgarantie, Technikpaket, Portal)"]
            if "wallbox" in history.data["data"]["extra_options"]:
                if history.data["data"].get("extra_options_wallbox_variant") == "senec-22kW":
                    update_data["extra_packages2"].append("Wallbox SENEC 22kW Pro")
                elif history.data["data"].get("extra_options_wallbox_variant") == "control-11kW":
                    update_data["extra_packages2"].append("Wallbox Heidelberger Energie Control (11KW)")
                elif history.data["data"].get("extra_options_wallbox_variant") == "senec-pro-11kW":
                    update_data["extra_packages2"].append("Wallbox SENEC pro S (11kW)")
                else:
                    update_data["extra_packages2"].append("Wallbox Heidelberger Home Eco (11KW)")
            if "new_power_closet" in history.data["data"]["extra_options"]:
                update_data["extra_packages2"].append("Zählerschrank")
            if "emergency_power_box" in history.data["data"]["extra_options"]:
                update_data["extra_packages2"].append("Notstrombox")
            if history.data["calculated"]["min_kwp_heatcloud"] > 0 and history.data["data"].get("has_heating_quote") is True:
                update_data["extra_packages2"].append("Wärme Cloud Paket (zusätzlicher Zählerplatz für Wärme)")
            if "tax_consult" in history.data["data"]["extra_options"]:
                update_data["tax_consultant"] = "Ja"
            if "wwwp" in history.data["data"]["extra_options"]:
                if history.data["data"]["extra_options_wwwp_variant"] == "NIBE L":
                    update_data["bwwp"] = ["Nibe 160"]
                if history.data["data"]["extra_options_wwwp_variant"] == "NIBE XL":
                    update_data["bwwp"] = ["Nibe 210"]

            if "module_kwp" in history.data["data"]:
                if history.data["data"]["module_kwp"]["label"] == "PV Modul SENEC.SOLAR 380 Watt BLACK":
                    update_data["pv_module"] = ["SENEC 380 Watt Modul"]
                elif history.data["data"]["module_kwp"]["label"] == "ASWS-415-MS-BW 415 Watt":
                    update_data["pv_module"] = ["415 Watt ASWS. Black"]
                else:
                    for value in [280, 320, 380, 400]:
                        if history.data["data"]["module_kwp"]["kWp"] * 1000 == value: ### todo auf produkte matchen
                            update_data["pv_module"] = [f"{value} Watt Amerisolar black"]
                            if value == 280:
                                update_data["pv_module"] = [f"{value} Watt Amerisolar"]
                            if value == 380:
                                update_data["pv_module"] = [f"{value} Watt Amerisolar Black"]
                print("asd", update_data["pv_module"])
            if history.data.get("construction_year") not in [None, "", "0", 0]:
                update_data["construction_date"] = datetime.datetime.strptime(f'{history.data["construction_year"]}-01-01', "%Y-%m-%d")
                update_data["construction_date"] = str(update_data["construction_date"] + datetime.timedelta(weeks=int(history.data["construction_week"])))

            update_data["count_modules"] = history.data["data"]["pv_count_modules"]

            update_data["emove_packet"] = history.data["data"]["emove_tarif"]

        update_data["quote_type"] = "keine Auswahl"
        update_data["quote_type3"] = ["keine Auswahl"]
        if history.data["data"].get("has_pv_quote") is True and history.data["data"].get("has_roof_reconstruction_quote") is True:
            update_data["quote_type"] = "Photovoltaik und Dachsanierung"
        else:
            if history.data["data"].get("has_pv_quote") is True:
                update_data["quote_type"] = "Photovoltaik"
            if history.data["data"].get("has_roof_reconstruction_quote") is True:
                update_data["quote_type"] = "Dachsanierung"
        if history.data["data"].get("has_pv_quote") is True:
            update_data["quote_type2"].append("Cloud/PV")
        if history.data["data"].get("has_heating_quote") is True:
            update_data["quote_type2"].append("Heizung")
            if history.data["data"].get("new_heating_type") == "gas":
                update_data["quote_type3"] = ["Heizung Gas"]
            if history.data["data"].get("new_heating_type") == "oli":
                update_data["quote_type3"] = ["Heizung Öl"]
            if history.data["data"].get("new_heating_type") in ["hybrid_gas", "heatpump"]:
                update_data["quote_type3"] = ["Heizung WP"]
                update_data["hwp"] = ["Ja"]
                if False and history.data["data"].get("has_pv_quote") is False:
                    if "new_power_closet" in history.data["data"]["extra_options"]:  ###   laksl
                        update_data["extra_packages2"].append("Zählerschrank")

        if history.data["data"].get("has_roof_reconstruction_quote") is True:
            update_data["quote_type2"].append("Dachsanierung")
        if history.data["data"].get("has_bluegen_quote") is True:
            update_data["quote_type2"].append("BlueGen")
        update_data["dz4_customer"] = "kein DZ-4 Kunde"
        update_data["energie360_financing"] = "Nein"
        if history.data["data"].get("has_pv_quote") is True \
            and history.data["data"].get("investment_type") == "financing" \
            and history.data["data"].get("financing_bank") == "energie360":
            update_data["energie360_financing"] = "Ja"
        if history.data["data"].get("has_heating_quote") is True \
            and history.data["data"].get("investment_type_heating") == "financing" \
            and history.data["data"].get("financing_bank_heating") == "energie360":
            update_data["energie360_financing"] = "Ja"
        if len(update_data["extra_packages2"]) == 0:
            update_data["extra_packages2"] = ["keine Auswahl"]
        update_deal(deal["id"], update_data)


def set_default_data(deal):
    if deal.get("cloud_number") not in [None, "", "0", 0]:
        return deal
    if deal.get("unique_identifier") in [None, "None", "0", 0, ""]:
        return None
    history = QuoteHistory.query.filter(QuoteHistory.lead_id == deal.get("unique_identifier")).order_by(QuoteHistory.datetime.desc()).first()
    if history is None:
        return None
    if history.data.get("data").get("cloud_number") in [None, "None", "0", 0, ""]:
        return None
    update_data = {}
    update_data["cloud_number"] = history.data.get("data").get("cloud_number")
    '''
                    "lightcloud_usage": "UF_CRM_1597757913754",
                    "heatcloud_usage": "UF_CRM_1597757931782",
                    "ecloud_usage": "UF_CRM_1607944188",
                    "cloud_monthly_cost": "UF_CRM_1612265225",
                    "cloud_yearly_usage": "UF_CRM_1585822072",
                    "has_emove_package": "UF_CRM_1620741780",
                    "emove_usage_inhouse": "UF_CRM_1620741150",
                    "emove_usage_outside": "UF_CRM_1620740831",
                    "is_negative_cloud": "UF_CRM_1607944340",
                    "cloud_runtime": "UF_CRM_1597758014166",
                    "counter_main": "UF_CRM_1585821761",
                    "counter_heatcloud": "UF_CRM_1597757955687",
                    "counter_ecloud": "UF_CRM_1611239704"'''
    update_deal(deal["id"], update_data)
    return get_deal(deal["id"])