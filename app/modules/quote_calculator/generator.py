import json
import math
import datetime
import io
import os
import requests
import copy
from flask import render_template
from PyPDF2 import PdfFileMerger, PdfFileWriter, PdfFileReader

from app.modules.settings import get_settings
from app.modules.external.bitrix24.user import get_user
from app.modules.external.bitrix24.drive import get_file_content, get_file_content_cached
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
            "quote_calculator/generator/footer2.html",
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
            margins=["0.3", "0.3", "0.6", "0.3"],
            landscape=True)
        return pdf
    return None


def generate_quote_pdf(lead_id, data, return_string=False, order_confirmation=False):
    config = get_settings(section="offer/pdf")
    config_general = get_settings(section="general")
    if data is not None:
        if "datetime" not in data:
            data["datetime"] = datetime.datetime.now()
        data["heading"] = "Angebot/Leistungsverzeichnis"
        if order_confirmation:
            set_confirmation_text(data)
        else:
            foreword_product = get_product("Vortext: Angebot PV", "Texte")
            if foreword_product is not None:
                data["foreword"] = foreword_product["DESCRIPTION"]
                data["foreword_type"] = foreword_product["DESCRIPTION_TYPE"]
            if data.get("has_special_condition", True) is False:
                appendix_product = get_product("Nachtext Angebot 8 Tage (ohne Kommentar)", "Texte")
            else:
                appendix_product = get_product("Nachtext Angebot 8 Tage", "Texte")
            if appendix_product is not None:
                data["appendix"] = appendix_product["DESCRIPTION"].replace("[[delivery_week_year]]", f'{data["construction_week"]}/{data["construction_year"]}')
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


def generate_roof_reconstruction_pdf(lead_id, data, return_string=False, order_confirmation=False):
    config = get_settings(section="offer/pdf")
    config_general = get_settings(section="general")
    if data is not None:
        if "datetime" not in data:
            data["datetime"] = datetime.datetime.now()
        if order_confirmation:
            set_confirmation_text(data)
        else:
            data["heading"] = "Angebot/Leistungsverzeichnis"
            foreword_product = get_product("Vortext: Angebot PV", "Texte")
            if foreword_product is not None:
                data["foreword"] = foreword_product["DESCRIPTION"]
                data["foreword_type"] = foreword_product["DESCRIPTION_TYPE"]

            if data.get("has_special_condition", True) is False:
                appendix_product = get_product("Nachtext Angebot 8 Tage Dach (ohne Kommentar)", "Texte")
            else:
                appendix_product = get_product("Nachtext Angebot 8 Tage Dach", "Texte")
            if appendix_product is not None:
                delivery_date = datetime.datetime.now() + datetime.timedelta(weeks=14)
                data["appendix"] = appendix_product["DESCRIPTION"].replace("[[delivery_week_year]]", delivery_date.strftime("%U/%Y"))
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


def generate_heating_pdf(lead_id, data, return_string=False, order_confirmation=False):
    config = get_settings(section="offer/pdf")
    config_general = get_settings(section="general")
    if data is not None:
        if "datetime" not in data:
            data["datetime"] = datetime.datetime.now()
        if order_confirmation:
            set_confirmation_text(data)
        else:
            data["heading"] = "Angebot/Leistungsverzeichnis"
            foreword_product = get_product("Vortext: Angebot PV", "Texte")
            if foreword_product is not None:
                data["foreword"] = foreword_product["DESCRIPTION"]
                data["foreword_type"] = foreword_product["DESCRIPTION_TYPE"]

            if data.get("has_special_condition", True) is False:
                appendix_product = get_product("Nachtext Angebot 8 Tage Heizung (ohne Kommentar)", "Texte")
            else:
                appendix_product = get_product("Nachtext Angebot 8 Tage Heizung", "Texte")
            if appendix_product is not None:
                delivery_date = datetime.datetime.now() + datetime.timedelta(weeks=16)
                data["appendix"] = appendix_product["DESCRIPTION"].replace("[[delivery_week_year]]", delivery_date.strftime("%U/%Y"))
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


def generate_bluegen_pdf(lead_id, data, return_string=False, order_confirmation=False):
    config = get_settings(section="offer/pdf")
    config_general = get_settings(section="general")
    if data is not None:
        if "datetime" not in data:
            data["datetime"] = datetime.datetime.now()
        if order_confirmation:
            set_confirmation_text(data)
        else:
            data["heading"] = "Angebot/Leistungsverzeichnis"
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
            "quote_calculator/generator/bluegen.html",
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


def generate_bluegen_wi_pdf(lead_id, data, return_string=False, order_confirmation=False):
    config = get_settings(section="offer/pdf")
    config_general = get_settings(section="general")
    if data is not None:
        data["base_url"] = config_general["base_url"]
        if "datetime" not in data:
            data["datetime"] = datetime.datetime.now()
        content = render_template(
            "quote_calculator/generator/bluegen-wi/index.html",
            base_url=config_general["base_url"],
            lead_id=lead_id,
            data=data
        )
        data["datetime"] = str(data["datetime"])
        if return_string:
            return content
        pdf = gotenberg_pdf(
            content,
            margins=["0", "0", "0", "0"],
            landscape=True)
        return pdf
    return None


def generate_datasheet_pdf(lead_id, data):
    config = get_settings(section="offer/datasheet_pdf")
    output_file = io.BytesIO()
    merger = PdfFileMerger()

    # PV
    if "has_pv_quote" in data["data"] and data["data"]["has_pv_quote"]:
        if "emergency_power_box" in data["data"]["extra_options"]:
            add_pdf_by_drive_id(merger, 438048, cached=True)
        if "wwwp" in data["data"]["extra_options"]:
            add_pdf_by_drive_id(merger, config["nibe_wp"], cached=True)
        if "wallbox" in data["data"]["extra_options"]:
            if "extra_options_wallbox_variant" in data["data"] and data["data"]["extra_options_wallbox_variant"] == "senec-22kW":
                add_pdf_by_drive_id(merger, 436174, cached=True)  # https://keso.bitrix24.de/disk/downloadFile/436174/?&ncc=1&filename=Senec+Wallbox.pdf
            elif "extra_options_wallbox_variant" in data["data"] and data["data"]["extra_options_wallbox_variant"] == "control-11kW":
                add_pdf_by_drive_id(merger, 2342388, cached=True)  # https://keso.bitrix24.de/disk/downloadFile/2342388/?&ncc=1&filename=322095_TDB_Wallbox_Energy_Control_DE_X3.pdf
            else:
                add_pdf_by_drive_id(merger, 2341958, cached=True)  # https://keso.bitrix24.de/disk/downloadFile/2341958/?&ncc=1&filename=322095_TDB_Wallbox_Home_Eco_DE_X3.pdf

        if "products" in data:
            pv_module = next((item for item in data["products"] if item["NAME"].find("Soluxtec Glas Glas 330 Watt") == 0), None)
            if pv_module is not None:
                add_pdf_by_drive_id(merger, 558088, cached=True)
            pv_module = next((item for item in data["products"] if item["NAME"].find("PV-Modul Amerisolar 280 Watt") == 0), None)
            if pv_module is not None:
                add_pdf_by_drive_id(merger, 436126, cached=True)
            pv_module = next((item for item in data["products"] if item["NAME"].find("PV-Modul Amerisolar 320 Watt") == 0), None)
            if pv_module is not None:
                add_pdf_by_drive_id(merger, 436124, cached=True)
            pv_module = next((item for item in data["products"] if item["NAME"].find("PV-Modul Amerisolar 380 Watt Black") == 0), None)
            if pv_module is not None:
                add_pdf_by_drive_id(merger, 1086940, cached=True)
            pv_module = next((item for item in data["products"] if item["NAME"].find("ASWS-415-MS-BW 415 Watt") == 0), None)
            if pv_module is not None:
                add_pdf_by_drive_id(merger, 3559146, cached=True)  # https://keso.bitrix24.de/disk/downloadFile/3559146/?&ncc=1&filename=datenblatt-ASWS-415-MS-BW-deutsch.pdf
            pv_module = next((item for item in data["products"] if item["NAME"].find("PV-Modul Amerisolar 400 Watt") == 0), None)
            if pv_module is not None:
                pv_module = next((item for item in data["products"] if item["NAME"].find("PV-Modul Amerisolar 400 Watt Black") == 0), None)
                if pv_module is not None:
                    add_pdf_by_drive_id(merger, 436158, cached=True)
                else:
                    add_pdf_by_drive_id(merger, 436128, cached=True)
            pv_module = next((item for item in data["products"] if item["NAME"].lower().find("senec lithium speicher") == 0), None)
            if pv_module is not None:
                add_pdf_by_drive_id(merger, 2341368, cached=True)  # https://keso.bitrix24.de/disk/downloadFile/2341368/?&ncc=1&filename=Senec+Home+Datenbla%CC%88tter+v2.1.pdf
            pv_module = next((item for item in data["products"] if item["NAME"].lower().find("senec v3") == 0), None)
            if pv_module is not None:
                add_pdf_by_drive_id(merger, 2341370, cached=True)  # https://keso.bitrix24.de/disk/downloadFile/2341370/?&ncc=1&filename=Senec+Home+Datenbla%CC%88tter+v3.pdf
        add_pdf_by_drive_id(merger, 436112, cached=True)  # zebra_zertifgikat
        add_pdf_by_drive_id(merger, 436106, cached=True)  # Testsieger Garantiebedingunegn
        add_pdf_by_drive_id(merger, 436102, cached=True)  # Kapazitätsversprechen
        if "solaredge" in data["data"]["extra_options"]:
            add_pdf_by_drive_id(merger, 2332216, cached=True)  # https://keso.bitrix24.de/disk/downloadFile/2332216/?&ncc=1&filename=Solaredge+gesamt.pdf
            if data["data"].get("pv_kwp", 0) > 30:
                add_pdf_by_drive_id(merger, 1352454, cached=True)  # https://keso.bitrix24.de/disk/downloadFile/1352454/?&ncc=1&filename=power-optimizer-datasheet-30.pdf
            else:
                add_pdf_by_drive_id(merger, 1352452, cached=True)  # https://keso.bitrix24.de/disk/downloadFile/1352452/?&ncc=1&filename=power-optimizer-datasheet.pdf
        if "tax_consult" in data["data"]["extra_options"]:
            add_pdf_by_drive_id(merger, 436100, cached=True)

    if "has_heating_quote" in data["data"] and data["data"]["has_heating_quote"]:
        if "new_heating_type" in data["data"] and data["data"]["new_heating_type"] == "heatpump":
            # add_pdf_by_drive_id(merger, 436226)  # password protected Waterkotte Wärmepumpen.pdf
            if data["data"].get("heating_quote_sqm", 0) > 300:
                add_pdf_by_drive_id(merger, 436222, cached=True)  # Nibe Wärmepumpen.pdf
                add_pdf_by_drive_id(merger, 2353740, cached=True)  # https://keso.bitrix24.de/disk/downloadFile/2353740/?&ncc=1&filename=Nibe+F2120+Technik.pdf
            else:
                add_pdf_by_drive_id(merger, 4511340, cached=True)  # https://keso.bitrix24.de/disk/downloadFile/4511340/?&ncc=1&filename=vaillant-wegweiser-modernisierung-einfamilienhaus-2309132.pdf
                add_pdf_by_drive_id(merger, 4511320, cached=True)  # https://keso.bitrix24.de/disk/downloadFile/4511320/?&ncc=1&filename=vaillant-systembroschuere-luftwasser-waermepumpen-2092159.pdf
        if "new_heating_type" in data["data"] and data["data"]["new_heating_type"] == "hybrid_gas":
            add_pdf_by_drive_id(merger, 2353742, cached=True)  # https://keso.bitrix24.de/disk/downloadFile/2353742/?&ncc=1&filename=Vaillant+Gas-Brennwert+ecoTec+plus+Technik.pdf
            add_pdf_by_drive_id(merger, 2353744, cached=True)  # https://keso.bitrix24.de/disk/downloadFile/2353744/?&ncc=1&filename=Vaillant+WP+arotherm-plus-Technische+Daten.pdf
    if "has_roof_reconstruction_quote" in data["data"] and data["data"]["has_roof_reconstruction_quote"]:
        add_pdf_by_drive_id(merger, 436216, cached=True)
        add_pdf_by_drive_id(merger, 436214, cached=True)
        if "reconstruction_roof_type" not in data["data"] or data["data"]["reconstruction_roof_type"] != "flat":
            add_pdf_by_drive_id(merger, 436212, cached=True)
    if "has_bluegen_quote" in data["data"] and data["data"]["has_bluegen_quote"]:
        if data["data"].get("bluegen_type") == "electa300":
            add_pdf_by_drive_id(merger, 2172962, cached=True)  # https://keso.bitrix24.de/disk/downloadFile/2172962/?&ncc=1&filename=Prospekt_eLecta300_05_2021_web.pdf
        else:
            add_pdf_by_drive_id(merger, 2356218, cached=True)  # https://keso.bitrix24.de/disk/downloadFile/2356218/?&ncc=1&filename=Brochure_Bluegen_DEU_WEB_Pagine_affiancate.pdf

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
    '''if "pdf_bluegen_file_id" in data and data["pdf_bluegen_file_id"] > 0:
        add_pdf_by_drive_id(merger, 459782, cached=True)'''
    if "pdf_bluegen_wi_file_id" in data and data["pdf_bluegen_wi_file_id"] > 0:
        add_pdf_by_drive_id(merger, data["pdf_bluegen_wi_file_id"])
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
    if "pdf_bluegen_file_id" in data and data["pdf_bluegen_file_id"] > 0:
        add_pdf_by_drive_id(merger, data["pdf_bluegen_file_id"])

    merger.write(output_file)
    merger.close()
    output_file.seek(0)
    pdf_content = output_file.read()
    return pdf_content


def generate_contract_summary_pdf(lead_id, data):
    config = get_settings(section="offer/summary_pdf")
    output_file = io.BytesIO()
    merger = PdfFileMerger()

    if "data" in data and data["data"].get("is_commercial") is True:
        add_pdf_by_drive_id(merger, 1598546, cached=True)  # https://keso.bitrix24.de/disk/downloadFile/1598546/?&ncc=1&filename=Verkaufsunterlagen+Gewerbe.pdf
    else:
        add_pdf_by_drive_id(merger, 443352, cached=True)  # Verkaufsunterlagen
    if datetime.datetime.now() >= datetime.datetime(2021,12,14,0,0,0):
        add_pdf_by_drive_id(merger, 2528314, cached=True)  # https://keso.bitrix24.de/disk/downloadFile/2528314/?&ncc=1&filename=contractingvertrag_januar_2022.pdf
    add_pdf_by_drive_id(merger, 443350, cached=True)  # Contractigvertrag
    add_pdf_by_drive_id(merger, 523230, cached=True)  # Abtretungsformular

    merger.write(output_file)
    merger.close()
    output_file.seek(0)
    pdf_content = output_file.read()
    return pdf_content


def generate_contract_summary_part1_pdf(lead_id, data):
    if "data" in data and data["data"].get("is_commercial") is True:
        return get_file_content_cached(1598546)  # https://keso.bitrix24.de/disk/downloadFile/1598546/?&ncc=1&filename=Verkaufsunterlagen+Gewerbe.pdf
    return get_file_content_cached(443352)  # Verkaufsunterlagen


def generate_contract_summary_part2_pdf(lead_id, data):
    return get_file_content_cached(523230)  # Abtretungsformular


def generate_contract_summary_part3_pdf(lead_id, data):
    if datetime.datetime.now() >= datetime.datetime(2021,12,14,0,0,0):
        return get_file_content_cached(2528314)  # https://keso.bitrix24.de/disk/downloadFile/2528314/?&ncc=1&filename=contractingvertrag_januar_2022.pdf
    return get_file_content_cached(443350)  # Contractigvertrag


def generate_contract_summary_part5_pdf(lead_id, data):
    return get_file_content_cached(4195114)  # Contractigvertrag WP https://keso.bitrix24.de/disk/downloadFile/4195114/?&ncc=1&filename=contracting_2022_formular.pdf


def generate_contract_summary_part4_pdf(lead_id, data, return_string=False):
    from app.utils.jinja_filters import dateformat, numberformat, currencyformat
    config_general = get_settings(section="general")
    if data is not None:

        old_heating_type = {
            'gas': 'Gas',
            'oil': 'Öl',
            'heatpump': 'Wärmepumpe',
            'pellez': 'Pellet',
            'electro': 'Elektro',
            'nightofen': 'Nachtspeicheröfen',
            'other': 'Sonstige'
        }
        heating_quote_old_heating_build = {
            '2-6_years': '2-6 Jahre',
            '7-12_years': '7-12 Jahre',
            'older': 'Über 12 Jahre'
        }
        new_usage = int(data.get("data", {}).get("heating_quote_usage"))
        if data.get("data", {}).get("new_heating_type") == "hybrid_gas":
            new_usage = int(data.get("data", {}).get("heating_quote_usage_wp"))
        auto_fill_fields = {
            "Bauvorhaben": data.get("contact", {}).get("firstname") + " " + data.get("contact", {}).get("lastname"),
            "Standort": data.get("contact", {}).get("zip") + " " + data.get("contact", {}).get("city"),
            "Erstellungsdatum": dateformat(data.get("datetime")),
            "Erstellungshinweise": f"Wärmepumpen Schnellauslegung | {data.get('contact', {}).get('lastname')} | {data.get('contact', {}).get('zip')} {data.get('contact', {}).get('city')} | Erstellungsdatum: {dateformat(data.get('datetime'))}",
            "Haustyp": "Neubau" if data.get("data", {}).get("heating_quote_house_build") == "new_building" else "Bestand",
            "Art_Hauses": data.get("data", {}).get("heating_quote_house_type"),
            "Derzeitiger_Verbrauch": "-" if data.get("data", {}).get("heating_quote_house_build") == "new_building" else numberformat(data.get("data", {}).get("heating_quote_usage_old"), digits=0) + " kWh",
            "Ursprung_Heizlastwertes": "Verbrauchsverfahren",
            "Warmwasserbereitung": "Über das Heizsystem" if data.get("data", {}).get("heating_quote_warm_water_type") == "heater" else "Nicht über das Heizsystem",
            "Wohnflache": str(data.get("data", {}).get("heating_quote_sqm")) + "m²",
            "Beheizte_Wohnflache": str(data.get("data", {}).get("heating_quote_sqm")) + "m²",
            "Personen": data.get("data", {}).get("heating_quote_people"),
            "Warmwasser_Heizsystem": "Ja" if data.get("data", {}).get("heating_quote_warm_water_type") == "heater" else "Nein" ,
            "Heizsystem": old_heating_type.get(data.get("data", {}).get("old_heating_type")),
            "Baujahr_Heizung": heating_quote_old_heating_build.get(data.get("data", {}).get("heating_quote_old_heating_build")),
            "Mittlerer_3_Jahre": "-" if data.get("data", {}).get("heating_quote_house_build") == "new_building" else numberformat(data.get("data", {}).get("heating_quote_usage_old"), digits=0) + " kWh",
            "Zirkulationspumpe": "Ja" if data.get("data", {}).get("heating_quote_circulation_pump") is True else "Nein",
            "Warmequelle": "Luft",
            "Betriebsweise": "Hybrid-System" if data.get("data", {}).get("new_heating_type") == "hybrid_gas" else "Monoenergetisch",
            "Radiatorheizkorper": data.get("data", {}).get("heating_quote_radiator_count"),
            "Bewohner": data.get("data", {}).get("heating_quote_people"),
            "Warmwassertemperatur": "50 - 55 °C",
            "Zirkulationspumpe_2": "Ja" if data.get("data", {}).get("heating_quote_circulation_pump") is True else "Nein",
            "Wasserkomfort": "Komfort",
            "Duschen": data.get("data", {}).get("heating_quote_shower_count"),
            "Badewannen": data.get("data", {}).get("heating_quote_bathtub_count"),
            "Stromverbrauch_Waermepumpe": numberformat(new_usage, digits=0),
            "Kostenlose_Umweltenergie": numberformat((new_usage * 3.6) - new_usage, digits=0),
            "Waermertrag": numberformat(new_usage * 3.6, digits=0),
            "Waermeumpentarif": numberformat(data.get("calculated", {}).get("heatcloud_extra_price_per_kwh", 0.2979) * 100, digits=2) + " Cent/kWh",
            "EnergiekostenProJahr": currencyformat(data.get("calculated", {}).get("heatcloud_extra_price_per_kwh", 0.2979) * new_usage),
            "Angenommener_pro_person": "50 l" if "extra_warm_water" in data.get("data", {}).get("heating_quote_extra_options", []) else "33.5 l",
        }
        if data.get("data", {}).get("heating_quote_radiator_type") == "floor_heating":
            auto_fill_fields["Heizkreis_1"] = "Fußbodenheizung - Vorlauftemperatur: ca. 35 °C"
            auto_fill_fields["Heizkreis_2"] = "-"
        if data.get("data", {}).get("heating_quote_radiator_type") == "mixed":
            auto_fill_fields["Heizkreis_1"] = "Fußbodenheizung - Vorlauftemperatur: ca. 35 °C"
            auto_fill_fields["Heizkreis_2"] = "Heizkörper - Vorlauftemperatur: ca. 50 °C"
        if data.get("data", {}).get("heating_quote_radiator_type") == "radiator_heating":
            auto_fill_fields["Heizkreis_1"] = "Heizkörper - Vorlauftemperatur: ca. 50 °C"
            auto_fill_fields["Heizkreis_2"] = "-"
        data["base_url"] = config_general["base_url"]
        if "datetime" not in data:
            data["datetime"] = datetime.datetime.now()
        content = render_template(
            "quote_calculator/generator/warmepumpe_wi/index.html",
            base_url=config_general["base_url"],
            lead_id=lead_id,
            data=data,
            fields=auto_fill_fields
        )
        data["datetime"] = str(data["datetime"])
        if return_string:
            return content
        overlay_pdf = PdfFileReader(io.BytesIO(gotenberg_pdf(
            content,
            margins=["0", "0", "0", "0"],
            landscape=False)))
        base_pdf = PdfFileReader(io.BytesIO(get_file_content_cached(3381834)))  # https://keso.bitrix24.de/disk/downloadFile/3381834/?&ncc=1&filename=waermepumpe_formular1.pdf
        pdf = PdfFileWriter()
        for i in range(0,9):
            if i in [0, 3, 4, 7]:
                page = overlay_pdf.getPage(i)
            else:
                page = overlay_pdf.getPage(i)
                page.mergePage(base_pdf.getPage(i))
            pdf.addPage(page)
        output = io.BytesIO()
        pdf.write(output)
        output.seek(0)
        return output.read()
    return None


def generate_order_confirmation_pdf(lead_id, data):
    config = get_settings(section="offer/summary_pdf")
    output_file = io.BytesIO()
    merger = PdfFileMerger()

    if "pdf_confirmation_pv_file_id" in data and data["pdf_confirmation_pv_file_id"] > 0:
        add_pdf_by_drive_id(merger, data["pdf_confirmation_pv_file_id"])
    if "pdf_confirmation_heating_file_id" in data and data["pdf_confirmation_heating_file_id"] > 0:
        add_pdf_by_drive_id(merger, data["pdf_confirmation_heating_file_id"])
    if "pdf_confirmation_roof_file_id" in data and data["pdf_confirmation_roof_file_id"] > 0:
        add_pdf_by_drive_id(merger, data["pdf_confirmation_roof_file_id"])
    if "pdf_confirmation_bluegen_file_id" in data and data["pdf_confirmation_bluegen_file_id"] > 0:
        add_pdf_by_drive_id(merger, data["pdf_confirmation_bluegen_file_id"])

    merger.write(output_file)
    merger.close()
    output_file.seek(0)
    pdf_content = output_file.read()
    return pdf_content


def generate_commission_pdf(lead_id, data, return_string=False, order_confirmation=False):
    config_general = get_settings(section="general")
    if data is not None:
        if "datetime" not in data:
            data["datetime"] = datetime.datetime.now()
        data["heading"] = "Provisionsaufstellung"
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
            "quote_calculator/generator/commission.html",
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


def generate_heatpump_auto_generate_pdf(lead_id, data):
    output_file = io.BytesIO()
    merger = PdfFileMerger()

    if data.get("pdf_quote_summary_file_id") not in [None, "", "0", 0, False]:
        add_pdf_by_drive_id(merger, data["pdf_quote_summary_file_id"])
    if data.get("pdf_contract_summary_part4_file_id") not in [None, "", "0", 0, False]:
        add_pdf_by_drive_id(merger, data["pdf_contract_summary_part4_file_id"])

    merger.write(output_file)
    merger.close()
    output_file.seek(0)
    pdf_content = output_file.read()
    return pdf_content


def set_confirmation_text(data):
    config_general = get_settings(section="general")
    data["heading"] = "Auftragsbestätigung"
    data["foreword"] = render_template(
        "quote_calculator/generator/order_confirmation/foreword.html",
        base_url=config_general["base_url"],
        data=data
    )
    data["foreword_type"] = "html"
    data["appendix"] = render_template(
        "quote_calculator/generator/order_confirmation/appendix.html",
        base_url=config_general["base_url"],
        data=data
    )
    data["appendix_type"] = "html"


def add_pdf_by_drive_id(merger, drive_id, cached=False):
    if cached:
        pdf = get_file_content_cached(drive_id)
    else:
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
