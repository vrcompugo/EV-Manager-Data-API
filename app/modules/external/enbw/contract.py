import json
import datetime

from app.exceptions import ApiException
from app.modules.external.bitrix24.deal import get_deal
from app.modules.external.bitrix24.contact import get_contact
from app.modules.cloud.services.contract import get_contract_data, normalize_date
from app.modules.settings import get_settings

from ._connector import post
from .models.enbw_contract import ENBWContract
from .models.enbw_contract_history import ENBWContractHistory


def send_contract(contract: ENBWContract):

    config = get_settings(section="external/enbw")
    deal = get_deal(contract.deal_id)
    contact = get_contact(deal.get("contact_id"))
    requested_usage = int(deal.get("delivery_usage")) * 0.5
    address_data = {
        "area_code": deal.get("delivery_zip"),
        "city": deal.get("delivery_city"),
        "email": contact.get("email")[0].get("VALUE"),
        "phone_number": contact.get("phone")[0].get("VALUE"),
        "street_name": deal.get("delivery_street"),
        "street_number": deal.get("delivery_street_nb"),
        "zipcode": deal.get("delivery_zip")
    }
    tarif_request = {
        "tariff_type": 1,
        "customer_type": 0,
        "client_type": 0,
        "counter_type": 0,
        "query_date": normalize_date(datetime.datetime.now()).strftime("%d.%m.%Y"),
        "brand": "0",
        "tariff_variant": 0,
        "consumption": requested_usage,
        "zip": address_data["zipcode"],
        "city": address_data["city"],
        "street": f'{address_data["street_name"]} {address_data["street_number"]}'
        }
    tarif_data = post("/tariffs", tarif_request, contract=contract)
    if "data" not in tarif_data or "tariffs" not in tarif_data["data"] or len(tarif_data["data"]["tariffs"]) == 0:
        raise ApiException("no valid tarif", "Kein ENBW Tariff für die Kundendaten gefunden")
    cheapest_tarif = None
    for tarif in tarif_data["data"]["tariffs"]:
        if cheapest_tarif is None or tarif["yearly_price"] < cheapest_tarif["yearly_price"]:
            cheapest_tarif = tarif
    if cheapest_tarif is None:
        raise ApiException("no valid tarif", "Kein ENBW Tariff für die Kundendaten gefunden")
    enbw_data = {
        "extern_id": config.get("extern_id"),
        "partner_id": config.get("partner_id"),
        "AddressData": address_data,
        "Client": {
            "account_holder": "energie360 GmbH & Co. KG",
            "account_iban": "DE84460628175191056500",
            "authorize_debit": 1,
            "bonus_cent": 0,
            "bonus_cent_runtime": 0,
            "bonus_percent": 0,
            "bonus_value": 0,
            "bonus_value_2": 0,
            "client_type": 0,
            "corDiff": 0,
            "counter_number": deal.get("delivery_counter_number"),
            "counter_type": "0",
            "previous_client_number": "",
            "previous_supplier": None,
            "previous_volume": requested_usage,
            "rate_ap": cheapest_tarif["rawSourceTariff"]["preise"][0]["arbeitspreis"]["brutto"],
            "rate_gp": cheapest_tarif["rawSourceTariff"]["preise"][0]["grundpreisJahr"]["brutto"],
            "self_terminated": "0",
            "sign_date": normalize_date(datetime.datetime.now()).strftime("%Y-%m-%d"),
            "agree_permission_date": normalize_date(datetime.datetime.now()).strftime("%Y-%m-%d"),
            "start_delivery": normalize_date(datetime.datetime.now()).strftime("%Y-%m-%d"),
            "start_delivery_next_possible": "1",
            "start_delivery_type": 1,
            "status": 0,
            "tariff_brand": cheapest_tarif["brand"],
            "tariff_city": address_data["city"],
            "tariff_energy_type": 1,
            "tariff_id": cheapest_tarif["base_tariff"]["tariff_id"],
            "campaign_identifier": cheapest_tarif["campaign"],
            "tariff_street": address_data["street_name"],
            "tariff_street_number": address_data["street_number"],
            "tariff_zip": address_data["zipcode"],
            "vp_client_extern_id": contract.sub_contract_number
        },
        "CorrespondenseAdressData": {
            "area_code": "34497",
            "city": "Korbach",
            "email": "versorger@energie360.de",
            "phone_number": "0 56 31 50 17 17",
            "street_name": "Marienburger Stra\u00dfe",
            "street_number": "6",
            "zipcode": "34497"
        },
        "CorrespondensePrivateData": {
            "first_name": "Andre",
            "last_name": "Schon",
            "suffix": "Herr"
        },
        "PrivateData": {
            "first_name": deal.get("delivery_first_name"),
            "last_name": deal.get("delivery_last_name"),
            "suffix": "Herr"
        }
    }

    contract_data = post("/clients", enbw_data, contract=contract)
    if contract_data is None:
        raise ApiException("transfer failed", "Übertragung an ENBW fehlgeschlagen")
    if "joulesId" not in contract_data or contract_data["joulesId"] is None:
        if  "message" in contract_data:
            raise ApiException("transfer failed", contract_data["message"])
        raise ApiException("transfer failed", "Übertragung an ENBW fehlgeschlagen")
    print(json.dumps(contract_data, indent=2))
    return contract_data