import json
import os
import time
from sqlalchemy import or_

from app import db
from app.models import Contract
from app.modules.settings import get_settings
from app.modules.cloud.services.contract import normalize_contract_number
from app.modules.external.bitrix24.deal import get_deal, get_deals, add_deal


def import_raw():
    dirname = os.path.dirname(__file__)
    for i in range(1,51):
        filename = f'{dirname}/raw/{i}.json'
        if os.path.exists(filename):
            print("import", i)
            with open(filename, 'r') as json_file:
                datas = json.load(json_file)
                for data in datas:
                    contract_number = data.get("identnummer")
                    main_contract_number = normalize_contract_number(contract_number)
                    contract = Contract.query.filter(Contract.contract_number == contract_number).first()
                    begin = data.get("liefernAb")
                    if begin == "0000-00-00T00:00:00.000Z":
                        begin = None
                    end = data.get("vertragsende")
                    if end == "0000-00-00T00:00:00.000Z":
                        end = None
                    if contract is None:
                        print('import', contract_number)
                        contract = Contract(
                            contract_number=contract_number,
                            main_contract_number=main_contract_number,
                            begin=begin,
                            end=end,
                            first_name=data.get("vorname"),
                            last_name=data.get("nachname"),
                            street=data.get("lsStrasse"),
                            street_nb=data.get("lsHausnummer"),
                            zip=data.get("lsPLZ"),
                            city=data.get("lsOrt"),
                            data=data
                        )
                        db.session.add(contract)
                    else:
                        contract.begin = begin
                        contract.end = end
                        contract.main_contract_number = main_contract_number
                    db.session.commit()

        else:
            with open(filename, 'w') as creating_new_json_file:
                pass


def import_contracts_for_anual_report():
    year = 2022
    system_config = get_settings(section="external/bitrix24")
    contracts = Contract.query \
        .filter(Contract.begin < f'{year + 1}-01-01')\
        .filter(or_(Contract.end.is_(None), Contract.end >= f'{year}-01-01'))
    for contract in contracts:
        if contract.main_contract_number is None:
            continue
        deals = get_deals({
            "SELECT": "full",
            f"FILTER[{system_config['deal']['fields']['cloud_contract_number']}]": contract.main_contract_number,
            "FILTER[CATEGORY_ID]": 126
        }, force_reload=True)
        time.sleep(2)
        if len(deals) == 0:
            deals2 = get_deals({
                "SELECT": "full",
                f"FILTER[{system_config['deal']['fields']['cloud_contract_number']}]": contract.main_contract_number,
                "FILTER[CATEGORY_ID]": 15
            }, force_reload=True)
            time.sleep(2)
            post_data = {
                "category_id": 126,
                "stage_id": "C126:UC_XM96DH",
                "title": contract.main_contract_number,
                "cloud_contract_number": contract.main_contract_number
            }
            if len(deals2) > 0:
                post_data["contact_id"] = deals2[0]["contact_id"]
                post_data["cloud_number"] = deals2[0]["cloud_number"]
            print("create", post_data)
            add_deal(post_data)
        else:
            print("exist", contract.main_contract_number)
