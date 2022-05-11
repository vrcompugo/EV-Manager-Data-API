import datetime
from importlib.resources import path
import json
import os
from random import random
import re
import pytz
from dateutil.parser import parse
from flask import Blueprint, Response, request, render_template, make_response
from sqlalchemy import or_, and_
from isodate import UTC
import zipfile
import tempfile
import shutil

from app import db
from app.decorators import api_response, log_request
from app.exceptions import ApiException
from app.modules.auth import validate_jwt, get_auth_info
from app.modules.auth.jwt_parser import encode_jwt
from app.modules.external.bitrix24.deal import get_deals, get_deal, update_deal
from app.modules.external.bitrix24.drive import add_file, get_public_link, get_folder_id, create_folder_path
from app.modules.settings import get_settings
from app.models import Order, OrderSchema, SherpaInvoice, SherpaInvoiceItem, ContractStatus, Contract, CounterValue
from .services.annual_statement import generate_annual_statement_pdf
from .services.contract import normalize_contract_number, get_contract_data, get_annual_statement_data, check_contract_data, generate_annual_report, generate_annual_report_pdf


blueprint = Blueprint("cloud2", __name__, template_folder='templates')


@blueprint.route("contract/<contract_number>", methods=['GET'])
@log_request
def get_contract(contract_number):
    auth_data = validate_jwt()
    if auth_data is None or "user" not in auth_data or auth_data["user"] is None:
        return "forbidden,", 401

    data = get_contract_data(contract_number)

    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')

@blueprint.route("contract/<contract_number>", methods=['POST'])
@log_request
def post_contract(contract_number):
    auth_data = validate_jwt()
    if auth_data is None or "user" not in auth_data or auth_data["user"] is None:
        return "forbidden,", 401

    data = get_contract_data(contract_number, force_reload=True)

    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


@blueprint.route("contract/<contract_number>/annual_statement/<year>", methods=['POST'])
@log_request
def post_contract_annual_statement_year(contract_number, year):
    auth_data = validate_jwt()
    if auth_data is None or "user" not in auth_data or auth_data["user"] is None:
        return "forbidden,", 401

    contract_status = ContractStatus.query.filter(ContractStatus.year == str(year)).filter(ContractStatus.contract_number == contract_number).first()
    if contract_status is None:
        contract_status = ContractStatus(
            year=str(year),
            contract_number=contract_number
        )
        db.session.add(contract_status)
        db.session.commit()

    data = generate_annual_report(contract_number, year)

    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


@blueprint.route("contract/<contract_number>/annual_statement/<year>/pdf", methods=['POST'])
@log_request
def post_contract_annual_statement_year_pdf(contract_number, year):
    auth_data = validate_jwt()
    if auth_data is None or "user" not in auth_data or auth_data["user"] is None:
        return "forbidden,", 401

    contract_status = ContractStatus.query.filter(ContractStatus.year == str(year)).filter(ContractStatus.contract_number == contract_number).first()
    if contract_status is None:
        contract_status = ContractStatus(
            year=str(year),
            contract_number=contract_number
        )
        db.session.add(contract_status)
        db.session.commit()

    data = generate_annual_report_pdf(contract_number, year)

    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


@blueprint.route("contract/<contract_number>/annual_statement/<year>", methods=['GET'])
@log_request
def post_contract_annual_statement_year2(contract_number, year):
    auth_data = validate_jwt()
    if auth_data is None or "user" not in auth_data or auth_data["user"] is None:
        return "forbidden,", 401

    return_string = False
    data = get_contract_data(contract_number)
    contract_status = ContractStatus.query.filter(ContractStatus.year == str(year)).filter(ContractStatus.contract_number == contract_number).first()
    statement = contract_status.data
    pdf = generate_annual_statement_pdf(data, statement, return_string)
    if return_string is True:
        return pdf

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filenam=export.pdf'
    return response


@blueprint.route("contract/<year>/list", methods=['GET'])
@log_request
def get_contract_list(year):
    auth_data = validate_jwt()
    if auth_data is None or "user" not in auth_data or auth_data["user"] is None:
        return "forbidden,", 401

    data = get_invoce_list(year)

    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


@blueprint.route("contract/<contract_number>/annual_statement/<year>/manuell_data", methods=['PUT'])
@log_request
def put_manuell_data(contract_number, year):
    auth_data = validate_jwt()
    if auth_data is None or "user" not in auth_data or auth_data["user"] is None:
        return "forbidden,", 401

    data = request.json

    status = ContractStatus.query\
        .filter(ContractStatus.contract_number == contract_number) \
        .filter(ContractStatus.year == year)\
        .first()
    print(data.get("data"))
    status.manuell_data = data.get("data")
    db.session.commit()
    print(data.get("data"), status.manuell_data)

    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


@blueprint.route("contract/counter_values", methods=['POST'])
@log_request
def add_counter_value():
    auth_data = validate_jwt()
    if auth_data is None or "user" not in auth_data or auth_data["user"] is None:
        return "forbidden,", 401

    data = request.json
    data = store_counter_value(data.get("counter"))

    return Response(
        json.dumps({"status": "success", "data": data.id}),
        status=200,
        mimetype='application/json')


@blueprint.route("contract/counter_values/<id>", methods=['PUT'])
@log_request
def edit_counter_value(id):
    auth_data = validate_jwt()
    if auth_data is None or "user" not in auth_data or auth_data["user"] is None:
        return "forbidden,", 401

    data = request.json
    data = store_counter_value(data.get("counter"))

    return Response(
        json.dumps({"status": "success", "data": data.id}),
        status=200,
        mimetype='application/json')


@blueprint.route("contract/counter_values/<counter_id>", methods=['DELETE'])
@log_request
def delete_counter_value(counter_id):
    auth_data = validate_jwt()
    if auth_data is None or "user" not in auth_data or auth_data["user"] is None:
        return "forbidden,", 401

    counter = CounterValue.query.filter(CounterValue.id == counter_id).first()
    if counter is not None:
        db.session.delete(counter)
        db.session.commit()

    return Response(
        json.dumps({"status": "success", "data": counter_id}),
        status=200,
        mimetype='application/json')


def store_counter_value(counter):
    if counter.get("id") is not None:
        storedCounter = CounterValue.query.filter(CounterValue.id == counter["id"]).first()
    else:
        storedCounter = CounterValue(
            number=counter.get("number"),
            origin="energie360"
        )
        db.session.add(storedCounter)
    storedCounter.date = counter.get("date")
    storedCounter.value = counter.get("value")
    db.session.commit()
    return storedCounter


@blueprint.route("contract/<contract_number>/check/<year>", methods=['GET'])
@log_request
def get_contract_check(contract_number, year):
    auth_data = validate_jwt()
    if auth_data is None or "user" not in auth_data or auth_data["user"] is None:
        return "forbidden,", 401

    data = check_contract_data(contract_number, year)

    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


def get_invoce_list(year):
    contracts = db.session.query(Contract)\
        .filter(or_(
            and_(
                Contract.begin >= f"{year}-01-01",
                Contract.begin <= f"{year}-12-31"
            ),
            Contract.begin.is_(None)
        )) \
        .order_by(Contract.contract_number.desc())
    data = []
    status_field_list = [
        "cloud_number",
        "has_lightcloud",
        "has_cloud_number",
        "has_begin_date",
        "has_smartme_number",
        "has_smartme_number_values",
        "has_smartme_number_heatcloud",
        "has_smartme_number_heatcloud_values",
        "has_correct_usage",
        "has_sherpa_values",
        "has_heatcloud",
        "has_ecloud",
        "has_consumers",
        "has_emove",
        "pdf_file_id",
        "pdf_file_link",
        "is_generated",
        "is_invoiced",
        "manuell_data",
        "status"
    ]
    for contract in contracts:
        invoice = db.session.query(SherpaInvoice) \
            .filter(SherpaInvoice.abrechnungszeitraum_von >= f"{year}-01-01") \
            .filter(SherpaInvoice.abrechnungszeitraum_von <= f"{year}-12-31") \
            .filter(SherpaInvoice.identnummer == contract.contract_number) \
            .first()
        status = ContractStatus.query\
            .filter(ContractStatus.contract_number == contract.contract_number)\
            .filter(ContractStatus.year == year)\
            .first()
        if invoice is None:
            item = {
                "contract_number": contract.contract_number,
                "invoice_number": "",
                "begin": None,
                "end": None,
                "power_meter_number": "",
                "usage": 0,
                "days": 0
            }
        else:
            item = {
                "contract_number": contract.contract_number,
                "invoice_number": invoice.rechnungsnummer,
                "begin": str(invoice.abrechnungszeitraum_von),
                "end": str(invoice.abrechnungszeitraum_bis),
                "power_meter_number": invoice.zahlernummer,
                "usage": invoice.verbrauch,
                "days": invoice.tage
            }
        for field in status_field_list:
            if status is not None:
                item[field] = getattr(status, field)
                if field == "manuell_data" and item[field] is None:
                    item[field] = {}
            else:
                item[field] = None
        data.append(item)
    return data


@blueprint.route("import", methods=[ 'POST'])
@api_response
@log_request
def post_invoices_upload_file():
    auth_data = validate_jwt()
    if auth_data is None or "user" not in auth_data or auth_data["user"] is None:
        return "forbidden,", 401
    invoices = request.files.get("invoices")
    if invoices is None:
        raise ApiException("no-file", "no file", 400)
    with zipfile.ZipFile(invoices, "r") as zip_file:
        temp_dir = tempfile.mkdtemp()
        if os.path.isdir(temp_dir):
            zip_file.extractall(temp_dir)
            for file in os.listdir(temp_dir):
                filepath = temp_dir + "/" + file
                if os.path.isfile(filepath) and filepath[-4:] == ".csv":
                    with open(filepath, "r") as csv_file:
                        rows = csv_file.readlines()
                    file_data = []
                    invoice_id = None
                    colums = rows[0].rstrip("\n").split(";")
                    del rows[0]
                    for index, row in enumerate(rows):
                        row = row.rstrip("\n").split(";")
                        row_data = {}
                        for index2 in range(len(row)):
                            row_data[colums[index2]] = row[index2]
                        if index == 0:
                            existing_invoice = SherpaInvoice.query\
                                .filter(SherpaInvoice.identnummer == normalize_contract_number(row_data.get("Identnummer")))\
                                .filter(SherpaInvoice.rechnungsnummer == row_data.get("Rechnungsnummer"))\
                                .filter(SherpaInvoice.abrechnungszeitraum_von == datetime.datetime.strptime(row_data.get("Abrechnungszeitraum von"), "%d.%m.%Y"))\
                                .filter(SherpaInvoice.abrechnungszeitraum_bis == datetime.datetime.strptime(row_data.get("Abrechnungszeitraum bis"), "%d.%m.%Y"))\
                                .first()
                            if existing_invoice is None:
                                invoice = SherpaInvoice(
                                    identnummer=normalize_contract_number(row_data.get("Identnummer")),
                                    rechnungsnummer=row_data.get("Rechnungsnummer"),
                                    abrechnungszeitraum_von=datetime.datetime.strptime(row_data.get("Abrechnungszeitraum von"), "%d.%m.%Y"),
                                    abrechnungszeitraum_bis=datetime.datetime.strptime(row_data.get("Abrechnungszeitraum bis"), "%d.%m.%Y"),
                                    zahlernummer=row_data.get("Zählernummer"),
                                    abrechnungsart=row_data.get("Abrechnungsart"),
                                    verbrauch=convert_sherpa_number(row_data, "Verbrauch"),
                                    tage=convert_sherpa_number(row_data, "Tage")
                                )
                                db.session.add(invoice)
                                db.session.flush()
                                invoice_id = invoice.id
                                print(invoice_id)
                        else:
                            if invoice_id is not None:
                                invoice_item = SherpaInvoiceItem(
                                    sherpa_invoice_id=invoice_id,
                                    zahlernummer=row_data.get("Zählernummer"),
                                    art_des_zahlerstandes=row_data.get("Art des Zählerstands"),
                                    zahlerart=row_data.get("Zählerart"),
                                    stand_alt=convert_sherpa_number(row_data, "Stand alt"),
                                    datum_stand_alt=datetime.datetime.strptime(row_data.get("Datum Stand alt"), "%d.%m.%Y"),
                                    ablesegrund=row_data.get("Ablesegrund"),
                                    stand_neu=convert_sherpa_number(row_data, "Stand neu"),
                                    datum_stand_neu=datetime.datetime.strptime(row_data.get("Datum Stand neu"), "%d.%m.%Y"),
                                    verbrauch=convert_sherpa_number(row_data, "Verbrauch"),
                                    tage=convert_sherpa_number(row_data, "Tage"),
                                    wandlerfaktor=row_data.get("Wandlerfaktor"),
                                )
                                db.session.add(invoice_item)
                    db.session.commit()

        shutil.rmtree(temp_dir)

    return Response(
        json.dumps({"status": "success", "data": 0}),
        status=200,
        mimetype='application/json')


@blueprint.route("import_contracts", methods=['POST'])
@api_response
@log_request
def post_contract_upload_file():
    auth_data = validate_jwt()
    if auth_data is None or "user" not in auth_data or auth_data["user"] is None:
        return "forbidden,", 401
    contracts = request.files.get("contracts")
    if contracts is None:
        raise ApiException("no-file", "no file", 400)
    data = json.load(contracts)
    print(len(data))
    for contract in data:
        contract_number = normalize_contract_number(contract.get("identnummer"))
        existing = Contract.query.filter(Contract.contract_number == contract_number).first()
        if existing is None:
            contract = Contract(
                contract_number=contract_number,
                first_name=contract.get("vorname"),
                last_name=contract.get("nachname"),
                street=contract.get("lsStrasse"),
                street_nb=contract.get("lsHausnummer"),
                zip=contract.get("lsPLZ"),
                city=contract.get("lsOrt")
            )
            db.session.add(contract)
            db.session.commit()
            print(contract_number)

    return Response(
        json.dumps({"status": "success", "data": 0}),
        status=200,
        mimetype='application/json')


@blueprint.route("contract/<deal_id>/annual_statement", methods=['GET', 'POST'])
@log_request
def get_contract_annual_statement():
    config = get_settings(section="external/bitrix24")
    auth_info = get_auth_info()
    if auth_info["user"] is None:
        return "Forbidden"
    token = encode_jwt(auth_info, expire_minutes=600)
    return render_template("cloud2/contract/annual_statement.html", token=token)


@blueprint.route("contract/<year>/listview", methods=['GET', 'POST'])
@log_request
def cloud2_listview(year):
    config = get_settings(section="external/bitrix24")
    auth_info = get_auth_info()
    if auth_info["user"] is None:
        return "Forbidden2"
    token = encode_jwt(auth_info, expire_minutes=600)
    return render_template("cloud2/list.html", token=token, year=year)


@blueprint.route("", methods=['GET', 'POST'])
def cloud2_index():
    config = get_settings(section="external/bitrix24")
    auth_info = get_auth_info()
    if auth_info["user"] is None:
        return "Forbidden2"
    contract_number = None
    options = request.form.get("PLACEMENT_OPTIONS")
    if options is None:
        return "Keine Placement Optionen gesetzt"
    options = json.loads(options)
    if request.form.get("PLACEMENT") == "CRM_DEAL_DETAIL_TAB":
        deal = get_deal(options["ID"])
        if deal is not None:
            contract_number = normalize_contract_number(deal.get("cloud_contract_number"))
    if contract_number is None:
        return "Keine Vertragsnummer gewählt"
    token = encode_jwt(auth_info, expire_minutes=600)
    return render_template("cloud2/index.html", token=token, contract_number=contract_number)


@blueprint.route("/install", methods=['GET', 'POST'])
def install_cloud2():
    env = os.getenv('ENVIRONMENT')
    return render_template("cloud2/install.html", domain=request.host, env=env)


@blueprint.route("/uninstall", methods=['POST'])
def uninstall_cloud2s():
    return render_template("cloud2/uninstall.html", domain=request.host)


def convert_sherpa_number(row_data, field):
    return int(float(row_data.get(field, "0").replace(",", ".")))