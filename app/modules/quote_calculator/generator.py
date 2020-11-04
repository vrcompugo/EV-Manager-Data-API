import json
import math
import datetime
import io
import os
import requests
import copy
from flask import render_template
from PyPDF2 import PdfFileMerger

from app.modules.settings import get_settings
from app.modules.external.bitrix24.user import get_user
from app.modules.external.bitrix24.drive import get_file_content
from app.modules.external.bitrix24.contact import get_contact
from app.modules.external.bitrix24.products import get_list as get_product_list, get_product
from app.modules.external.bitrix24._field_values import convert_field_euro_from_remote
from app.modules.cloud.services.calculation import calculate_cloud as get_cloud_calculation
from app.utils.gotenberg import gotenberg_pdf
from app.utils.jinja_filters import currencyformat, numberformat
from app.utils.pdf_form_filler import update_form_values, get_form_fields


def generate_cover_pdf(lead_id, data, return_string=False):
    config = get_settings(section="offer/pdf")
    config_general = get_settings(section="general")
    if data is not None:
        if "datetime" not in data:
            data["datetime"] = datetime.datetime.now()

        letter_text = get_product("Anschreiben Angebot", "Texte")
        if letter_text is not None:
            data["letter_text"] = letter_text["DESCRIPTION"]
            data["letter_text_type"] = letter_text["DESCRIPTION_TYPE"]

        content = render_template(
            "quote_calculator/generator/cover.html",
            base_url=config_general["base_url"],
            lead_id=lead_id,
            data=data,
            heading=" "
        )
        data["datetime"] = str(data["datetime"])
        if return_string:
            return content
        pdf = gotenberg_pdf(
            content,
            landscape=True,
            margins=["0", "0", "0", "0"])
        return pdf
    return None


def generate_letter_pdf(lead_id, data, return_string=False):
    config = get_settings(section="offer/pdf")
    config_general = get_settings(section="general")
    if data is not None:
        if "datetime" not in data:
            data["datetime"] = datetime.datetime.now()

        letter_text = get_product("Anschreiben Angebot", "Texte")
        if letter_text is not None:
            data["letter_text"] = letter_text["DESCRIPTION"]
            data["letter_text_type"] = letter_text["DESCRIPTION_TYPE"]

        header_content = render_template(
            "quote_calculator/generator/header.html",
            base_url=config_general["base_url"],
            lead_id=lead_id,
            data=data
        )
        footer_content = render_template(
            "quote_calculator/generator/footer.html",
            base_url=config_general["base_url"],
            lead_id=lead_id,
            data=data
        )
        content = render_template(
            "quote_calculator/generator/letter.html",
            base_url=config_general["base_url"],
            lead_id=lead_id,
            data=data,
            heading=" "
        )
        data["datetime"] = str(data["datetime"])
        if return_string:
            return content
        pdf = gotenberg_pdf(
            content,
            content_header=header_content,
            content_footer=footer_content,
            landscape=True)
        return pdf
    return None


def generate_quote_pdf(lead_id, data, return_string=False):
    config = get_settings(section="offer/pdf")
    config_general = get_settings(section="general")
    if data is not None:
        if "datetime" not in data:
            data["datetime"] = datetime.datetime.now()
        foreword_product = get_product("Vortext: Angebot PV", "Texte")
        if foreword_product is not None:
            data["foreword"] = foreword_product["DESCRIPTION"]
            data["foreword_type"] = foreword_product["DESCRIPTION_TYPE"]

        appendix_product = get_product("Nachtext Angebot 8 Tage", "Texte")
        if appendix_product is not None:
            data["appendix"] = appendix_product["DESCRIPTION"]
            data["appendix_type"] = appendix_product["DESCRIPTION_TYPE"]
        header_content = render_template(
            "quote_calculator/generator/header.html",
            base_url=config_general["base_url"],
            lead_id=lead_id,
            data=data
        )
        footer_content = render_template(
            "quote_calculator/generator/footer.html",
            base_url=config_general["base_url"],
            lead_id=lead_id,
            data=data
        )
        content = render_template(
            "quote_calculator/generator/index.html",
            base_url=config_general["base_url"],
            lead_id=lead_id,
            data=data
        )
        data["datetime"] = str(data["datetime"])
        if return_string:
            return content
        pdf = gotenberg_pdf(
            content,
            content_header=header_content,
            content_footer=footer_content,
            landscape=False)
        return pdf
    return None


def generate_roof_reconstruction_pdf(lead_id, data, return_string=False):
    config = get_settings(section="offer/pdf")
    config_general = get_settings(section="general")
    if data is not None:
        if "datetime" not in data:
            data["datetime"] = datetime.datetime.now()
        foreword_product = get_product("Vortext: Angebot PV", "Texte")
        if foreword_product is not None:
            data["foreword"] = foreword_product["DESCRIPTION"]
            data["foreword_type"] = foreword_product["DESCRIPTION_TYPE"]

        appendix_product = get_product("Nachtext Angebot 8 Tage", "Texte")
        if appendix_product is not None:
            data["appendix"] = appendix_product["DESCRIPTION"]
            data["appendix_type"] = appendix_product["DESCRIPTION_TYPE"]
        header_content = render_template(
            "quote_calculator/generator/header.html",
            base_url=config_general["base_url"],
            lead_id=lead_id,
            data=data
        )
        footer_content = render_template(
            "quote_calculator/generator/footer.html",
            base_url=config_general["base_url"],
            lead_id=lead_id,
            data=data
        )
        content = render_template(
            "quote_calculator/generator/roof.html",
            base_url=config_general["base_url"],
            lead_id=lead_id,
            data=data
        )
        data["datetime"] = str(data["datetime"])
        if return_string:
            return content
        pdf = gotenberg_pdf(
            content,
            content_header=header_content,
            content_footer=footer_content,
            landscape=False)
        return pdf
    return None


def generate_heating_pdf(lead_id, data, return_string=False):
    config = get_settings(section="offer/pdf")
    config_general = get_settings(section="general")
    if data is not None:
        if "datetime" not in data:
            data["datetime"] = datetime.datetime.now()
        foreword_product = get_product("Vortext: Angebot PV", "Texte")
        if foreword_product is not None:
            data["foreword"] = foreword_product["DESCRIPTION"]
            data["foreword_type"] = foreword_product["DESCRIPTION_TYPE"]

        appendix_product = get_product("Nachtext Angebot 8 Tage", "Texte")
        if appendix_product is not None:
            data["appendix"] = appendix_product["DESCRIPTION"]
            data["appendix_type"] = appendix_product["DESCRIPTION_TYPE"]
        header_content = render_template(
            "quote_calculator/generator/header.html",
            base_url=config_general["base_url"],
            lead_id=lead_id,
            data=data
        )
        footer_content = render_template(
            "quote_calculator/generator/footer.html",
            base_url=config_general["base_url"],
            lead_id=lead_id,
            data=data
        )
        content = render_template(
            "quote_calculator/generator/heating.html",
            base_url=config_general["base_url"],
            lead_id=lead_id,
            data=data
        )
        data["datetime"] = str(data["datetime"])
        if return_string:
            return content
        pdf = gotenberg_pdf(
            content,
            content_header=header_content,
            content_footer=footer_content,
            landscape=False)
        return pdf
    return None


def generate_datasheet_pdf(lead_id, data):
    config = get_settings(section="offer/datasheet_pdf")
    output_file = io.BytesIO()
    merger = PdfFileMerger()

    # PV
    if "has_pv_quote" in data["data"] and data["data"]["has_pv_quote"]:
        if "emergency_power_box" in data["data"]["extra_options"]:
            add_pdf_by_drive_id(merger, 438048)
        if "wwwp" in data["data"]["extra_options"]:
            add_pdf_by_drive_id(merger, 436218)
        add_pdf_by_drive_id(merger, 436174)  # senec wallbox

        if "products" in data:
            pv_module = next((item for item in data["products"] if item["NAME"].find("PV-Modul Amerisolar 280 Watt") == 0), None)
            if pv_module is not None:
                add_pdf_by_drive_id(merger, 436126)
            pv_module = next((item for item in data["products"] if item["NAME"].find("PV-Modul Amerisolar 320 Watt") == 0), None)
            if pv_module is not None:
                add_pdf_by_drive_id(merger, 436124)
            pv_module = next((item for item in data["products"] if item["NAME"].find("PV-Modul Amerisolar 400 Watt") == 0), None)
            if pv_module is not None:
                pv_module = next((item for item in data["products"] if item["NAME"].find("PV-Modul Amerisolar 400 Watt Black") == 0), None)
                if pv_module is not None:
                    add_pdf_by_drive_id(merger, 436158)
                else:
                    add_pdf_by_drive_id(merger, 436128)
            pv_module = next((item for item in data["products"] if item["NAME"].find("Senec V2.1") == 0), None)
            if pv_module is not None:
                add_pdf_by_drive_id(merger, 443354)
            pv_module = next((item for item in data["products"] if item["NAME"].find("Senec V3") == 0), None)
            if pv_module is not None:
                add_pdf_by_drive_id(merger, 436116)
        add_pdf_by_drive_id(merger, 436112)  # zebra_zertifgikat
        add_pdf_by_drive_id(merger, 436106)  # Testsieger Garantiebedingunegn
        add_pdf_by_drive_id(merger, 436102)  # Kapazitätsversprechen
        if "tax_consult" in data["data"]["extra_options"]:
            add_pdf_by_drive_id(merger, 436100)

    if "has_heating_quote" in data["data"] and data["data"]["has_heating_quote"]:
        if "new_heating_type" in data["data"] and data["data"]["new_heating_type"] == "heatpump":
            # add_pdf_by_drive_id(merger, 436226)  # password protected watterkote
            add_pdf_by_drive_id(merger, 436222)
    if "has_roof_reconstruction_quote" in data["data"] and data["data"]["has_roof_reconstruction_quote"]:
        add_pdf_by_drive_id(merger, 436216)
        add_pdf_by_drive_id(merger, 436214)
        if "reconstruction_roof_type" not in data["data"] or data["data"]["reconstruction_roof_type"] != "flat":
            add_pdf_by_drive_id(merger, 436212)

    merger.write(output_file)
    merger.close()
    output_file.seek(0)
    pdf_content = output_file.read()
    return pdf_content


def generate_summary_pdf(lead_id, data):
    config = get_settings(section="offer/summary_pdf")
    output_file = io.BytesIO()
    merger = PdfFileMerger()

    customer_name = ""
    if "contact" in data:
        customer_name = data["contact"]["name"] + " " + data["contact"]["last_name"]
    add_pdf_by_drive_id(merger, data["pdf_cover_file_id"])
    add_pdf_by_drive_id(merger, data["pdf_letter_file_id"])
    if "pdf_wi_file_id" in data and data["pdf_wi_file_id"] > 0:
        add_pdf_by_drive_id(merger, data["pdf_wi_file_id"])
    merger.write(output_file)
    merger.close()
    output_file.seek(0)
    pdf_content = output_file.read()
    return pdf_content


def generate_quote_summary_pdf(lead_id, data):
    config = get_settings(section="offer/summary_pdf")
    output_file = io.BytesIO()
    merger = PdfFileMerger()

    if "pdf_pv_file_id" in data and data["pdf_pv_file_id"] > 0:
        add_pdf_by_drive_id(merger, data["pdf_pv_file_id"])
    if "pdf_cloud_config_file_id" in data and data["pdf_cloud_config_file_id"] > 0:
        add_pdf_by_drive_id(merger, data["pdf_cloud_config_file_id"])
    if "pdf_heating_file_id" in data and data["pdf_heating_file_id"] > 0:
        add_pdf_by_drive_id(merger, data["pdf_heating_file_id"])
    if "pdf_roof_file_id" in data and data["pdf_roof_file_id"] > 0:
        add_pdf_by_drive_id(merger, data["pdf_roof_file_id"])

    merger.write(output_file)
    merger.close()
    output_file.seek(0)
    pdf_content = output_file.read()
    return pdf_content


def generate_contract_summary_pdf(lead_id, data):
    config = get_settings(section="offer/summary_pdf")
    output_file = io.BytesIO()
    merger = PdfFileMerger()

    if "has_heating_quote" in data["data"] and data["data"]["has_heating_quote"]:
        if "new_heating_type" in data["data"] and data["data"]["new_heating_type"] == "heatpump":
            add_pdf_by_drive_id(merger, 443348)
    add_pdf_by_drive_id(merger, 443352)  # Verkaufsunterlagen
    add_pdf_by_drive_id(merger, 443350)  # Contractigvertrag

    merger.write(output_file)
    merger.close()
    output_file.seek(0)
    pdf_content = output_file.read()
    return pdf_content


def add_pdf_by_drive_id(merger, drive_id):
    pdf = get_file_content(drive_id)
    pdf_file = io.BytesIO(pdf)
    pdf_file.seek(0)
    merger.append(pdf_file)


def add_pdf_by_link(merger, url):
    result = requests.get(url)
    pdf = result.content
    pdf_file = io.BytesIO(pdf)
    pdf_file.seek(0)
    merger.append(pdf_file)
