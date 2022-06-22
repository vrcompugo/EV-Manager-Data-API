import json
from dateutil.parser import parse

from app.modules.external.bitrix24.contact import get_contact
from app.modules.cloud.services.contract import get_contract_data
from app.modules.settings import get_settings


def send_contract(contract_number):
    contract_number = "C2205307037"

    config = get_settings(section="external/enbw")
    contract = get_contract_data(contract_number)
    contact = get_contact(contract.get("contact_id"))
    enbw_data = {
        "partner_id": config.get("partner_id"),
        "CorrespondenseAdressData": {
            "area_code": contact.get("zip"),
            "city": contact.get("city"),
            "email": contact.get("email")[0].get("VALUE"),
            "phone_number": contact.get("phone")[0].get("VALUE"),
            "street_name": contact.get("street"),
            "street_number": contact.get("street_nb"),
            "zipcode": contact.get("zip")
        },
        "CorrespondensePrivateData": {
            "first_name": contact.get("firstname"),
            "last_name": contact.get("lastname"),
            "suffix": contact.get("salutation")
        },
        "PrivateData": {
            "first_name": "Petra",
            "last_name": "Testkunde",
            "suffix": contact.get("salutation")
        },
        "permissions": {
            "datetime": "08052018000000",
            "admissionText": "",
            "admissionTextVersion": "YELLO_BELEHRUNG_002",
            "admissionChannels": ["E-Mail","SMS"],
            "admissionPurposes": ["Strom"],
            "consentText": "Ja",
            "consentTextVersion": "YELLO_ENERGIE_S_003",
            "consentConfirmed": True,
            "consentChannels": ["Telefon","E-Mail","SMS"],
            "consentPurposes": [
                "Strom",
                "Gas",
                "EnergienaheDienstleistungen",
                "Photovoltaik"
            ]
        }
    }
    for cloud_config in contract.get("configs"):
        customer_products = []
        for index, consumer in enumerate(cloud_config["consumers"]):
            customer_products.append(f"consumer{index}")
            cloud_config[f"consumer{index}"] = consumer
        products = ["lightcloud", "heatcloud"] + customer_products
        for product in products:
            if product not in enbw_data and product in cloud_config and cloud_config.get(product).get("delivery_begin") not in [None, "", 0, "0"]:
                enbw_data[product] = {
                    "extern_id": f"{contract_number}-{product}",
                    "AddressData": {
                        "area_code": contact.get("delivery_zip"),
                        "city": contact.get("delivery_city"),
                        "email": contact.get("email")[0].get("VALUE"),
                        "phone_number": contact.get("phone")[0].get("VALUE"),
                        "street_name": contact.get("delivery_street"),
                        "street_number": contact.get("delivery_street_nb"),
                        "zipcode": contact.get("delivery_zip")
                    },
                    "Client": {
                        "account_holder": config.get("account_holder"),
                        "account_iban":  config.get("account_iban"),
                        "authorize_debit": 1,
                        "bonus_cent": 0,
                        "bonus_cent_runtime": 0,
                        "bonus_percent": 0,
                        "bonus_value": 0,
                        "bonus_value_2": 0,
                        "client_type": 0,
                        "corDiff": 0,
                        "counter_number": cloud_config.get(product).get("power_meter_number"),
                        "counter_type": "0",
                        "previous_client_number": "",
                        "previous_supplier": contract.get("main_deal").get("energie_delivery_provider"),
                        "previous_volume": str(cloud_config.get(product).get("usage")),
                        "rate_ap": .0,
                        "rate_gp": .0,
                        "self_terminated": "0",
                        "sign_date": contract.get("main_deal").get("order_sign_date"),
                        "start_delivery": cloud_config.get(product).get("delivery_begin"),
                        "start_delivery_next_possible": "1",
                        "start_delivery_type": 1,
                        "status": 0,
                        "tariff_brand": "enbw",
                        "tariff_city": contact.get("delivery_city"),
                        "tariff_energy_type": 1,
                        "tariff_id": "S_WV_HS_ET_P_AKTIVIMMO_01",
                        "campaign_identifier": "WWUDIREKTVERTRIEBNVKEINBONUS",
                        "tariff_street": contact.get("delivery_street"),
                        "tariff_street_number": contact.get("delivery_street_nb"),
                        "tariff_zip": contact.get("delivery_zip"),
                        "vp_client_extern_id": f"{contract_number}-{product}"
                    },
                }
    print(json.dumps(enbw_data, indent=2))