import datetime
from importlib.resources import path
import json
import os
from random import random
import re
import pytz
from dateutil.parser import parse
from flask import Blueprint, Response, request, render_template, make_response
from isodate import UTC
import zipfile
import tempfile
import shutil

from app import db
from app.decorators import api_response
from app.exceptions import ApiException
from app.modules.auth import validate_jwt, get_auth_info
from app.modules.auth.jwt_parser import encode_jwt
from app.modules.external.bitrix24.deal import get_deals, get_deal
from app.modules.external.bitrix24.drive import add_file, get_public_link, get_folder_id, create_folder_path
from app.modules.settings import get_settings
from app.models import Order, OrderSchema, SherpaInvoice, SherpaInvoiceItem
from .services.annual_statement import generate_annual_statement_pdf
from .services.contract import normalize_contract_number, get_contract_data, get_annual_statement_data


blueprint = Blueprint("cloud2", __name__, template_folder='templates')


@blueprint.route("contract/<contract_number>", methods=['GET'])
def get_contract(contract_number):
    auth_data = validate_jwt()
    if auth_data is None or "user" not in auth_data or auth_data["user"] is None:
        return "forbidden,", 401

    data = get_contract_data(contract_number)

    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


@blueprint.route("contract/<contract_number>/annual_statement/<year>", methods=['POST'])
def post_contract_annual_statement_year(contract_number, year):
    auth_data = validate_jwt()
    if auth_data is None or "user" not in auth_data or auth_data["user"] is None:
        return "forbidden,", 401

    data = get_contract_data(contract_number)
    if "annualStatements" not in data:
        data["annualStatements"] = []

    pdf = generate_annual_statement_pdf(data, year)
    print(f"Cloud/Kunde {data['contact_id']}/Vertrag {data['contract_number']}")
    subfolder_id = create_folder_path(415280, path=f"Cloud/Kunde {data['contact_id']}/Vertrag {data['contract_number']}")  # https://keso.bitrix24.de/docs/path/Kundenordner/

    statement = next((item for item in data["annualStatements"] if item["year"] == year), None)
    if statement is None:
        statement = {
            "year": year
        }
    statement["drive_id"] = add_file(folder_id=subfolder_id, data={
        "file_content": pdf,
        "filename": f"Cloud Abrechnung {year}.pdf"
    })
    statement["pdf_link"] = get_public_link(statement["drive_id"])

    data["annualStatements"].append(statement)
    return Response(
        json.dumps({"status": "success", "data": data}),
        status=200,
        mimetype='application/json')


@blueprint.route("contract/<contract_number>/annual_statement/<year>", methods=['GET'])
def post_contract_annual_statement_year2(contract_number, year):
    auth_data = validate_jwt()
    if auth_data is None or "user" not in auth_data or auth_data["user"] is None:
        return "forbidden,", 401

    return_string = False
    data = get_contract_data(contract_number)
    statement = get_annual_statement_data(data, year)
    pdf = generate_annual_statement_pdf(data, statement, return_string)
    if return_string is True:
        return pdf

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filenam=export.pdf'
    return response


@blueprint.route("import", methods=[ 'POST'])
@api_response
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


@blueprint.route("contract/<deal_id>/annual_statement", methods=['GET', 'POST'])
def get_contract_annual_statement():
    config = get_settings(section="external/bitrix24")
    auth_info = get_auth_info()
    if auth_info["user"] is None:
        return "Forbidden"
    token = encode_jwt(auth_info, expire_minutes=600)
    return render_template("cloud2/contract/annual_statement.html", token=token)


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