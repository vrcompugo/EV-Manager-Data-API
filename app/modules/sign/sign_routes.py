import json
import datetime

from flask import Blueprint, request, render_template, redirect, make_response, Response

from app import db
from app.decorators import token_required, api_response, log_request
from app.exceptions import ApiException
from app.models import InsignLog
from app.modules.auth.jwt_parser import decode_jwt, encode_jwt, encode_shared_jwt
from app.modules.settings import get_settings
from app.modules.quote_calculator.models.quote_history import QuoteHistory
from app.modules.external.bitrix24.task import add_task
from app.modules.external.bitrix24.deal import get_deal, update_deal
from app.modules.external.bitrix24.lead import get_lead, update_lead
from app.modules.external.bitrix24.drive import get_file, get_file_content, get_folder_id, add_file, get_public_link, create_folder_path


blueprint = Blueprint("sign", __name__, template_folder='templates')


@blueprint.route("/callbacks/follow_quote/<token>", methods=['GET', 'POST'])
@log_request
def get_insign_callback(token):
    from app.modules.external.insign.signature import download_file

    config = get_settings("external/bitrix24/folder_creation")
    token_data = decode_jwt(token)
    session_id = request.args.get("sessionid")
    event_type = request.args.get("eventid")
    if event_type != "EXTERNBEARBEITUNGFERTIG":
        return Response(
            '{"status": "error", "error_code": "drive_upload_failed", "message": "bitrix drive upload failed"}',
            status=200,
            mimetype='application/json')

    myprotal_folder = next((item for item in config["folders"] if item["key"] == "drive_myportal_folder"), None)
    lead = get_lead(token_data["unique_identifier"])
    customer_folder_id = get_folder_id(myprotal_folder["folder_id"], path=f"Kunde {lead['contact_id']}/Vertragsunterlagen")
    if customer_folder_id is None:
        customer_folder_id = create_folder_path(myprotal_folder["folder_id"], path=f"Kunde {lead['contact_id']}/Vertragsunterlagen")
    collection_files = []
    for file in token_data.get("documents", []):
        file_content = download_file(sessionId=session_id, file_id=file["id"])
        if isinstance(file_content, dict):
            error_response = json.dumps({
                "status": "error",
                "error_code": "document_download_failed",
                "message": f"GET /get/document s:{session_id} d:{file['id']} did respond with error in data",
                "data": file_content
            }, indent=2)
            return Response(
                error_response,
                status=400,
                mimetype='application/json')
        else:
            file_id = add_file(customer_folder_id, {
                "filename": token_data["number"] + " " + file["displayname"] + ".pdf",
                "file_content": file_content
            })
            if file_id is not None:
                collection_files.append({
                    "id": file_id,
                    "filename": file["displayname"] + ".pdf"
                })
    if len(collection_files) > 0:
        jwt = encode_shared_jwt(data={
            "files": collection_files
        }, expire_minutes=343200)
        deal_data = {
            "collection_url": f"https://kunden.energie360.de/files/collection?token={jwt['token']}",
            "order_sign_date": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S-01:00")
        }
        deal = get_deal(token_data["deal_id"])
        if deal.get("stage_id") in ["C220:UC_8OMM5X", "C220:PREPARATION", "C220:PREPAYMENT_INVOI"]:
            deal_data["stage_id"] = "C220:EXECUTING"
        else:
            title = f"Neue Unterschrift {deal['title']}"
            description = f"Unterschrift ist erfolgt für Auftrag: https://keso.bitrix24.de/crm/deal/details/{deal['id']}/"
            add_task({
                "fields[TITLE]": title,
                "fields[DESCRIPTION]": description,
                "fields[RESPONSIBLE_ID]": 670,
                "fields[DEADLINE]": str(datetime.datetime.now() + datetime.timedelta(days=14))
            })
        update_deal(token_data["deal_id"], deal_data)
        print("updated")
    log = InsignLog.query.filter(InsignLog.session_id == session_id).first()
    if log is not None:
        data = json.loads(json.dumps(log.data))
        data["final_response"] = str(datetime.datetime.now())
        log.data = data
        db.session.commit()
    return Response(
            '{"status": "error", "error_code": "drive_upload_failed", "message": "bitrix drive upload failed"}',
            status=200,
            mimetype='application/json')


@blueprint.route("/<token>", methods=['GET'])
@log_request
def redirect_to_insign(token):
    from app.modules.external.insign.signature import get_public_url

    try:
        print(token)
        token_data = decode_jwt(token) # { "deal_id": ..., "contract_number": ..., "cloud_number": ... }
    except Exception as e:
        print(e)
        return render_template("sign/error.html", error="Link nicht mehr gültig")
    deal = get_deal(token_data["deal_id"])
    if deal is None:
        return render_template("sign/error.html", error="Kein kompatibles Angebot gefunden. 1")

    lead_id = int(deal.get("unique_identifier"))
    history = db.session.query(QuoteHistory).filter(QuoteHistory.lead_id == lead_id).order_by(QuoteHistory.datetime.desc()).first()
    if history is None or history.data.get("cloud_number") != token_data["cloud_number"]:
        return render_template("sign/error.html", error="Kein kompatibles Angebot gefunden. 2")
    data = json.loads(json.dumps(history.data))
    data["contract_number"] = deal.get("contract_number")
    data["deal_id"] = deal.get("id")
    sessionId = get_insign_session_follow_interim_quote(data)
    try:
        email = data["contact"]["email"][0]["VALUE"]
    except Exception as e:
        email = "platzhalter@energie360.de"
    public_url = get_public_url(sessionId, email)
    return redirect(public_url, code=302)


def get_insign_session_follow_interim_quote(data):
    from app.modules.external.insign.signature import get_session_id
    from app.utils.jinja_filters import numberformat
    config = get_settings("general")
    signatures = [
        {
            "id": "mainsig",
            "displayname": "Unterschrift",
            "textsearch": f"__main_sig__",
            "required": True
        }
    ]
    documents = []
    prefillable_documents = []
    if "pdf_cloud_config_file_id" in data and data["pdf_cloud_config_file_id"] > 0:
        documents.append({
            "id": data["pdf_cloud_config_file_id"],
            "displayname": "Cloud-Angebot",
            "signatures": signatures
        })
    prefillable_documents.append({
        "id": 523230, # https://keso.bitrix24.de/disk/downloadFile/523230/?&ncc=1&filename=Abrettungsformular.pdf
        "displayname": "Abrettungsformular",
        "preFilledFields": []
    })
    prefillable_documents.append({
        "id": 2528314, # https://keso.bitrix24.de/disk/downloadFile/2528314/?&ncc=1&filename=contractingvertrag_januar_2022.pdf
        "displayname": "Contractigvertrag",
        "preFilledFields": []
    })
    prefillable_documents.append({
        "id": 5400174,  # https://keso.bitrix24.de/disk/downloadFile/5400174/?&ncc=1&filename=energie360-vollmacht.pdf
        "displayname": "Maklervollmacht",
        "preFilledFields": []
    })
    prefillable_documents.append({
        "id": 5898063,  # https://keso.bitrix24.de/disk/downloadFile/5898063/?&ncc=1&filename=AGBCLOUD360.pdf
        "displayname": "AGB",
        "preFilledFields": []
    })
    auto_fill_fields = [
        { "id": "Name und Vorname", "text": data.get("contact", {}).get("firstname") + " " + data.get("contact", {}).get("lastname") },
        { "id": "name vorname 1", "text": data.get("contact", {}).get("firstname") + " " + data.get("contact", {}).get("lastname") },
        { "id": "Name, Vorname ", "text": data.get("contact", {}).get("firstname") + " " + data.get("contact", {}).get("lastname") },
        { "id": "Name", "text": data.get("contact", {}).get("firstname") + " " + data.get("contact", {}).get("lastname") },
        { "id": "Vorname", "text": data.get("contact", {}).get("firstname") },
        { "id": "Nachname", "text": data.get("contact", {}).get("lastname") },
        { "id": "Strasse", "text": data.get("contact", {}).get("street") },
        { "id": "Hausnummer", "text": data.get("contact", {}).get("street_nb") },
        { "id": "Straße Hausnr", "text": data.get("contact", {}).get("street") + " " + data.get("contact", {}).get("street_nb") },
        { "id": "PLZ", "text": data.get("contact", {}).get("zip") },
        { "id": "Ort", "text": data.get("contact", {}).get("city") },
        { "id": "Wohnort", "text": data.get("contact", {}).get("city") },
        { "id": "Standort", "text": data.get("contact", {}).get("zip") + " " + data.get("contact", {}).get("city") },
        { "id": "PLZ, Ort", "text": data.get("contact", {}).get("zip") + " " + data.get("contact", {}).get("city") },
        { "id": "PLZ Ort", "text": data.get("contact", {}).get("zip") + " " + data.get("contact", {}).get("city") },
        { "id": "Anschrift", "text": data.get("contact", {}).get("street") + " " + data.get("contact", {}).get("street_nb") + " " + data.get("contact", {}).get("zip") + " " + data.get("contact", {}).get("city") },
        { "id": "Kwp Nennleistung", "text": numberformat(data.get("data", {}).get("pv_kwp")) },
        { "id": "IBAN", "text": data.get("data", {}).get("iban") },
        { "id": "BIC", "text": data.get("data", {}).get("bic") },
        { "id": "Zähler Nummer", "text": data.get("data", {}).get("power_meter_number") },
        { "id": "Wärme Zählernummer", "text": data.get("data", {}).get("heatcloud_power_meter_number") },
        { "id": "malo id", "text": data.get("data", {}).get("main_malo_id") },
        { "id": "Geburtsdatum", "text": data.get("data", {}).get("birthdate") }
    ]
    for field in auto_fill_fields:
        for n in range(-1,7):
            suffix = n
            if n == -1:
                suffix = ""
            for document in prefillable_documents:
                document["preFilledFields"].append({
                    "id": f"{field['id']}#{suffix}",
                    "text": field['text']
                })
                document["preFilledFields"].append({
                    "id": f"{field['id']}{suffix}",
                    "text": field['text']
                })

    for document in prefillable_documents:
        documents.append(document)
    token_documents = json.loads(json.dumps(documents))
    for document in token_documents:
        if "preFilledFields" in document:
            del document["preFilledFields"]
    token_data = {
            "unique_identifier": data["id"],
            "deal_id": data["deal_id"],
            "number": data["number"],
            "contract_number": data["contract_number"],
            "documents": token_documents
        }
    token = encode_jwt(token_data, 172800)
    return get_session_id(
        {
            "displayname": data["number"],
            "foruser": data["assigned_by_id"] + " " + data["assigned_user"]["EMAIL"],
            "callbackURL": "https://www.energie360.de/insign-callback/",
            "userFullName": f'{data["assigned_user"]["NAME"]} {data["assigned_user"]["LAST_NAME"]}',
            "userEmail": data["assigned_user"]["EMAIL"],
            "serverSidecallbackURL": f"{config['base_url']}sign/callbacks/follow_quote/{token['token']}",
            "documents": documents
        },
        data.get("id")
    )

