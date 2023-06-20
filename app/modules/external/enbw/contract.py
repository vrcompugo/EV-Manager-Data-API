import json
import datetime
import base64
from werkzeug import FileStorage
from sqlalchemy import or_

from app import db
from app.exceptions import ApiException
from app.modules.external.bitrix24.deal import get_deal, update_deal
from app.modules.external.bitrix24.contact import get_contact
from app.modules.external.bitrix24.drive import get_folder_id, get_folder, get_file_content
from app.modules.cloud.services.contract import get_contract_data, normalize_date
from app.modules.settings import get_settings

from ._connector import post, get_ftp_file, rename_ftp_file
from .tarif import get_tarifs
from .models.enbw_contract import ENBWContract
from .models.enbw_contract_history import ENBWContractHistory


def send_contract(contract: ENBWContract, contract_file: FileStorage, tarif_id, is_terminated=False):

    config = get_settings(section="external/enbw")
    deal = get_deal(contract.deal_id, force_reload=True)
    contact = get_contact(deal.get("contact_id"))
    requested_usage = int(deal.get("delivery_usage")) * 0.5
    contract_files = []
    if contract_file is not None:
        file_content = contract_file.read()
        contract_files = [{
            "file_type": "contract",
            "name": "Vertrag.pdf",
            "content": base64.b64encode(file_content).decode('utf-8')
        }]
    else:
        contract_folder_id = get_folder_id(parent_folder_id=442678, path=f"Vorgang {deal.get('unique_identifier')}/Uploads/Vertragsunterlagen")
        if contract_folder_id is not None:
            files = get_folder(contract_folder_id)
            for file in files:
                if file.get("NAME").find("Maklervollmacht") >= 0:
                    file_content = get_file_content(file.get("ID"))
                    contract_files = [{
                        "file_type": "contract",
                        "name": "Vertrag.pdf",
                        "content": base64.b64encode(file_content).decode('utf-8')
                    }]
    if len(contract_files) == 0:
        raise ApiException("no valid contract file", "Keine Maklervollmacht-PDF gefunden")
    address_data = {
        "area_code": "05631",
        "city": deal.get("delivery_city"),
        "email": "",
        # "phone_number": contact.get("phone")[0].get("VALUE"),
        "phone_number": "501717",
        "street_name": deal.get("delivery_street"),
        "street_number": deal.get("delivery_street_nb"),
        "zipcode": deal.get("delivery_zip")
    }
    tarif = None
    tarifs = get_tarifs(contract)
    for item in tarifs:
        if str(item["base_tariff_id"]) == str(tarif_id):
            tarif = item
            break
    if tarif is None:
        raise ApiException("no valid tarif", f"{tarif_id} ENBW Tariff nicht gefunden")
    contract.tarif_data = tarif
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
            "corDiff": 1,
            "counter_number": deal.get("delivery_counter_number"),
            "malo": deal.get("malo_lightcloud"),
            "counter_type": "0",
            "previous_client_number": "",
            "previous_supplier": deal.get("energie_delivery_code"),
            "previous_volume": requested_usage,
            "rate_ap": tarif["rawSourceTariff"]["preise"][0]["arbeitspreis"]["brutto"],
            "rate_gp": tarif["rawSourceTariff"]["preise"][0]["grundpreisJahr"]["brutto"],
            "self_terminated": "0",
            "sign_date": normalize_date(datetime.datetime.now()).strftime("%Y-%m-%d"),
            "agree_permission_date": normalize_date(datetime.datetime.now()).strftime("%Y-%m-%d"),
            "start_delivery": normalize_date(datetime.datetime.now()).strftime("%Y-%m-%d"),
            "start_delivery_next_possible": "1",
            "start_delivery_type": 1,
            "preferred_billing_date": normalize_date(datetime.datetime.now()).strftime("%Y-12-31"),
            "status": 0,
            "tariff_brand": tarif["brand"],
            "tariff_city": address_data["city"],
            "tariff_energy_type": 1,
            "tariff_id": tarif["base_tariff"]["tariff_id"],
            "campaign_identifier": tarif["campaign"],
            "tariff_street": address_data["street_name"],
            "tariff_street_number": address_data["street_number"],
            "tariff_zip": address_data["zipcode"],
            "vp_client_extern_id": contract.sub_contract_number
        },
        "CorrespondenseAddressData": {
            "area_code": "34497",
            "city": "Korbach",
            "email": "versorger@energie360.de",
            "phone_number": "0 56 31 50 17 17",
            "street_name": "Marienburger Stra\u00dfe",
            "street_number": "6",
            "zipcode": "34497"
        },
        "CorrespondensePrivateData": {
            "first_name": "-",
            "last_name": "Energie360 GmbH & Co. KG",
            "suffix": "Herr"
        },
        "PrivateData": {
            "first_name": deal.get("delivery_first_name"),
            "last_name": deal.get("delivery_last_name"),
            "suffix": "Herr"
        },
        "files": contract_files
    }
    if deal.get("is_cloud_heatcloud") in ["1", "Y", True, "true"]:
        enbw_data["Client"]["tariff_energy_type"] = 2
    if is_terminated:
        enbw_data["Client"]["self_terminated"] = "1"
        enbw_data["Client"]["start_delivery_next_possible"] = "0"
    contract_data = post("/clients", enbw_data, contract=contract)
    if contract_data is None:
        raise ApiException("transfer failed", "Übertragung an ENBW fehlgeschlagen")
    if "joulesId" not in contract_data or contract_data["joulesId"] is None:
        if  "message" in contract_data:
            raise ApiException("transfer failed", contract_data["message"])
        raise ApiException("transfer failed", "Übertragung an ENBW fehlgeschlagen")
    update_deal(deal.get("id"), {
        "contract_managed_by": "ENBW",
        "contract_transfered_at": str(datetime.datetime.now()),
    })
    return contract_data


def cron_update_contract_status():
    csv_filename = 'status/status_historie_latest.csv'
    csv_newfilename = f'status/status_historie_latest_{str(datetime.datetime.now())}.csv'
    csv_file = get_ftp_file(csv_filename)
    if csv_file is None:
        return
    lines = csv_file.split("\n")
    for line in lines:
        values = line.split(";")
        for index, value in enumerate(values):
            values[index] = value.replace('"', '')
        if values[0] in ["JoulesID", ""]:
            continue
        print(values)
        contract = ENBWContract.query.filter(ENBWContract.joulesId == values[0]).first()
        if contract is None:
            contract = ENBWContract.query.filter(ENBWContract.sub_contract_number == values[1]).first()
        history = ENBWContractHistory.query\
            .filter(ENBWContractHistory.datetime == values[4])\
            .filter(ENBWContractHistory.api_response_status == values[5])
        if contract is not None:
            history = history.filter(ENBWContractHistory.enbw_contract_id == contract.id)
        history = history.first()
        if history is None:
            history = ENBWContractHistory()
            if contract is not None:
                history.enbw_contract_id = contract.id
            if contract.enbw_contract_number is None:
                contract.enbw_contract_number = values[3]
                update_deal(contract.deal_id, {
                    "enbw_contract_number": values[3]
                })
            history.datetime = values[4]
            history.action = 'cron'
            history.post_data = None
            history.api_response_status = values[5]
            history.api_response = None
            history.api_response_raw = ";".join(values)
            deal = get_deal(contract.deal_id, force_reload=True)
            if deal.get("stage_id") in ["C15:UC_R6HWHP", "C15:UC_A8XIOF"]:
                if values[5] in ["Besttigt", "Bestätigt"]:
                    update_deal(contract.deal_id, {
                        "cloud_delivery_begin": values[6],
                        "stage_id": "C15:UC_D88VXL"
                    })
                    contract.status = "success"
                    contract.status_message = "Bestätigt"
                if values[5] in ["Error"]:
                    if contract.enbw_contract_number in [None, "", 0, "0"]:
                        update_deal(contract.deal_id, {
                            "stage_id": "C15:UC_A8XIOF"
                        })
                    else:
                        update_deal(contract.deal_id, {
                            "stage_id": "C15:UC_U3M2IG"
                        })
                    contract.status = "error"
                    contract.status_message = "Error"
            db.session.add(history)
            db.session.commit()
    rename_ftp_file(csv_filename, csv_newfilename)


def process_existing_enbw_contracts():
    histories = ENBWContractHistory.query.filter(or_(ENBWContractHistory.api_response_status == "Besttigt", ENBWContractHistory.api_response_status == "Error")).all()
    for history in histories:
        contract = history.contract
        deal = get_deal(contract.deal_id, force_reload=True)
        if deal.get("stage_id") not in ["C15:UC_R6HWHP"]:
            continue
        if history.api_response_status in ["Besttigt", "Bestätigt"]:
            values = history.api_response_raw.split(";")
            update_deal(contract.deal_id, {
                "cloud_delivery_begin": values[5],
                "stage_id": "C15:UC_D88VXL"
            })
            contract.status = "success"
            contract.status_message = "Bestätigt"
        if history.api_response_status in ["Error"]:
            if contract.enbw_contract_number in [None, "", 0, "0"]:
                update_deal(contract.deal_id, {
                    "stage_id": "C15:UC_A8XIOF"
                })
            else:
                update_deal(contract.deal_id, {
                    "stage_id": "C15:UC_U3M2IG"
                })
            contract.status = "error"
            contract.status_message = "Error"
    db.session.commit()