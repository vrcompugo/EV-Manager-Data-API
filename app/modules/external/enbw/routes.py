
from flask import Blueprint, request
import json

from app import db
from app.exceptions import ApiException
from app.decorators import api_response, log_request
from app.modules.auth import get_auth_info
from app.modules.auth.jwt_parser import decode_jwt, encode_jwt, encode_shared_jwt
from app.modules.external.bitrix24.deal import get_deal
from app.modules.cloud.services.contract import normalize_contract_number

from .contract import send_contract
from .tarif import get_tarifs
from .models.enbw_contract import ENBWContract
from .models.enbw_contract_history import ENBWContractHistory


blueprint = Blueprint("enbw", __name__, template_folder='templates')


@blueprint.route("/tarif/<deal_id>", methods=['GET'])
@api_response
@log_request
def get_tarifs_route(deal_id):
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return {"status": "failed", "data": {}, "message": "auth failed"}
    deal = get_deal(deal_id, force_reload=True)
    if deal is None:
        return {"status": "failed", "data": {}, "message": "deal not found"}
    if deal.get("cloud_contract_number") in [None, "", 0, "0"]:
        return {"status": "failed", "data": {}, "message": "keine vertragsnummer hinterlegt"}
    sub_contract_number = deal.get("cloud_contract_number")
    main_contract_number = normalize_contract_number(deal.get("cloud_contract_number"))
    contract = ENBWContract.query.filter(ENBWContract.sub_contract_number == sub_contract_number).first()
    if contract is None:
        contract = ENBWContract(
            main_contract_number=main_contract_number,
            sub_contract_number=sub_contract_number,
            deal_id=deal.get("id"),
            status=None
        )
        db.session.add(contract)
        db.session.commit()
    try:
        tarifs = get_tarifs(contract)
    except ApiException as e:
        contract.status = "error"
        contract.status_message = e.message
        db.session.commit()
        raise e
    except Exception as e:
        contract.status = "error"
        contract.status_message = str(e)
        db.session.commit()
        raise e

    return {"status": "success", "data": tarifs}


@blueprint.route("/contract", methods=['POST'])
@api_response
@log_request
def upload_contract():
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return {"status": "failed", "data": {}, "message": "auth failed"}
    data = request.form
    contract_file = request.files.get("contract_file")
    if data is None or data.get("deal_id") is None:
        return {"status": "failed", "data": {}, "message": "no id"}
    if data.get("tarif") in [None, "", 0]:
        return {"status": "failed", "data": {}, "message": "no tarif"}
    tarif_id = data.get("tarif")
    deal = get_deal(data.get("deal_id"), force_reload=True)
    if deal is None:
        return {"status": "failed", "data": {}, "message": "deal not found"}
    if deal.get("cloud_contract_number") in [None, "", 0, "0"]:
        return {"status": "failed", "data": {}, "message": "keine vertragsnummer hinterlegt"}
    sub_contract_number = deal.get("cloud_contract_number")
    main_contract_number = normalize_contract_number(deal.get("cloud_contract_number"))
    contract = ENBWContract.query.filter(ENBWContract.sub_contract_number == sub_contract_number).first()
    if contract is not None:
        if contract.status is not None and contract.status != "error":
            if contract.deal_id == deal.get("id"):
                return {"status": "failed", "data": {}, "message": "Bereits übertragen"}
            else:
                return {"status": "failed", "data": {}, "message": f"Achtung! Bereits übertragen durch Auftrag ID: {contract.deal_id}"}
    is_terminated = False
    if data.get("is_terminated") in ["true", "True", "1", 1, True]:
        is_terminated = True
    if contract is None:
        contract = ENBWContract(
            main_contract_number=main_contract_number,
            sub_contract_number=sub_contract_number,
            deal_id=deal.get("id"),
            status=None
        )
        db.session.add(contract)
        db.session.commit()
    try:
        contract_data = send_contract(contract, contract_file, tarif_id, is_terminated)
        contract.joulesId = contract_data.get("joulesId")
        contract.status = "transfered"
        contract.status_message = "Übertragen an ENBW. Warten auf Rückmeldung"
        db.session.commit()

    except ApiException as e:
        contract.status = "error"
        contract.status_message = e.message
        db.session.commit()
        raise e
    except Exception as e:
        contract.status = "error"
        contract.status_message = str(e)
        db.session.commit()
        raise e

    deal["enbw_data"] = contract.to_dict()
    if isinstance(deal["enbw_data"].get("files"), list):
        for file in deal["enbw_data"].get("files"):
            file["content"] = '...'

    return {"status": "success", "data": deal}