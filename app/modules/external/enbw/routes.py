
from flask import Blueprint, request

from app import db
from app.exceptions import ApiException
from app.decorators import api_response, log_request
from app.modules.auth import get_auth_info
from app.modules.auth.jwt_parser import decode_jwt, encode_jwt, encode_shared_jwt
from app.modules.external.bitrix24.deal import get_deal
from app.modules.cloud.services.contract import normalize_contract_number

from .contract import send_contract
from .models.enbw_contract import ENBWContract
from .models.enbw_contract_history import ENBWContractHistory


blueprint = Blueprint("enbw", __name__, template_folder='templates')



@blueprint.route("/contract", methods=['POST'])
@api_response
@log_request
def upload_contract():
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return {"status": "failed", "data": {}, "message": "auth failed"}
    data = request.json
    if data is None or data.get("id") is None:
        return {"status": "failed", "data": {}, "message": "no id"}
    deal = get_deal(data.get("id"))
    if deal is None:
        return {"status": "failed", "data": {}, "message": "deal not found"}
    sub_contract_number = deal.get("cloud_contract_number")
    main_contract_number = normalize_contract_number(deal.get("cloud_contract_number"))
    contract = ENBWContract.query.filter(ENBWContract.sub_contract_number == sub_contract_number).first()
    if contract is not None:
        if contract.status is not None and contract.status != "error":
            if contract.deal_id == deal.get("id"):
                return {"status": "failed", "data": {}, "message": "Bereits übertragen"}
            else:
                return {"status": "failed", "data": {}, "message": f"Achtung! Bereits übertragen durch Auftrag ID: {contract.deal_id}"}
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
        contract_data = send_contract(contract)
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

    return {"status": "success", "data": deal}