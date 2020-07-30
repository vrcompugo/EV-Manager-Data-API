
import pdfkit
import json
from flask import render_template, request, make_response
from PyPDF2 import PdfFileWriter, PdfFileReader
from io import StringIO, BytesIO
import dateutil

from app.modules.settings.settings_services import get_one_item as get_settings
from app.modules.file.file_services import add_item as add_file, update_item as update_file
from app.models import OfferV2, S3File
from app.utils.gotenberg import generate_pdf as gotenberg_pdf
from app.modules.cloud.services.calculation import cloud_offer_calculation_by_pv_offer

from ..offer_generation.cloud_offer import cloud_offer_items_by_pv_offer


def calculate_feasibility_study(offer: OfferV2):
    settings = get_settings("pv-settings")
    if settings is None:
        return None
    in_use_date = offer.datetime + dateutil.relativedelta.relativedelta(months=1)
    if offer.offer_group == "cloud-offer":
        cloud_runtime = 2
        if offer.data["price_guarantee"] == "10_years":
            cloud_runtime = 10
        cloud_calulation = offer.calculated
        consumer = 1
        usage = 1000
        run_time = 30
        price_increase = 5.75
        inflation_rate = 2.5
        packet = 50
        orientation = "west"
        orientation_label = "West/Ost"
        pv_efficiancy = settings["data"]["wi_settings"]["pv_efficiancy"]["west_east"]
        cloud_total = float(offer.total)
        if "emove_tarif" in offer.data:
            emove_tarif = offer.data["emove_tarif"]
        cloud_zero = False
    else:
        cloud_runtime = 12
        cloud_total = 0
        cloud_zero = False
        if "pv_options" in offer.survey.data:
            for option in offer.survey.data["pv_options"]:
                if option["label"] == "ZERO-Paket" and "is_selected" in option and option["is_selected"]:
                    cloud_zero = True

        cloud_calulation = cloud_offer_calculation_by_pv_offer(offer)
        if "cloud_emove" in offer.survey.data:
            emove_tarif = offer.survey.data["cloud_emove"]
        cloud_total = cloud_calulation["cloud_price_incl_refund"]
        if cloud_zero:
            cloud_total = cloud_total - cloud_calulation["cloud_price_light"]
            cloud_calulation["cloud_price_light"] = 0
        consumer = 1
        if "has_extra_drains" in offer.survey.data and offer.survey.data["has_extra_drains"]:
            for drain in offer.survey.data["extra_drains"]:
                if "usage" in drain and drain["usage"] != "" and int(drain["usage"]) > 0:
                    consumer = consumer + 1
        orientation_label = "West/Ost"
        pv_efficiancy = settings["data"]["wi_settings"]["pv_efficiancy"]["west_east"]
        if "direction" in offer.survey.data["roof_datas"][0]:
            if offer.survey.data["roof_datas"][0]["direction"] == "south":
                orientation_label = "Süd"
                pv_efficiancy = settings["data"]["wi_settings"]["pv_efficiancy"]["south"]
            if offer.survey.data["roof_datas"][0]["direction"] == "north":
                orientation_label = "Nord"
                pv_efficiancy = settings["data"]["wi_settings"]["pv_efficiancy"]["north"]
        else:
            offer.survey.data["roof_datas"][0]["direction"] = "west"

        usage = float(offer.survey.data["pv_usage"])
        if "has_extra_drains" in offer.survey.data and offer.survey.data["has_extra_drains"]:
            for drain in offer.survey.data["extra_drains"]:
                if "usage" in drain and drain["usage"] != "" and int(drain["usage"]) > 0:
                    usage = usage + float(drain["usage"])
        run_time = 30
        if "run_time" in offer.survey.data:
            run_time = int(offer.survey.data["run_time"])
        price_increase = 5.75
        if "price_increase" in offer.survey.data:
            price_increase = float(offer.survey.data["price_increase"])
        inflation_rate = 2.5
        if "inflation_rate" in offer.survey.data:
            inflation_rate = float(offer.survey.data["inflation_rate"])
        packet = int(offer.survey.data["packet_number"])
        orientation = offer.survey.data["roof_datas"][0]["direction"]
        orientation_label = "Süd" if offer.survey.data["roof_datas"][0]["direction"] == "south" else "West/Ost"
    data = {
        "cloud_runtime": cloud_runtime,
        "runtime": run_time,
        "cloud_zero": cloud_zero,
        "usage": usage,
        "paket": packet,
        "pv_efficiancy": pv_efficiancy,
        "orientation": orientation,
        "orientation_label": orientation_label,
        "in_use_date": in_use_date,
        "conventional_base_cost_per_year": settings["data"]["wi_settings"]["conventional_base_cost_per_year"],
        "conventional_base_cost_per_kwh": settings["data"]["wi_settings"]["conventional_base_cost_per_kwh"],
        "cost_increase_rate": price_increase,
        "inflation_rate": inflation_rate,
        "full_cost_increase_rate": price_increase + inflation_rate,
        "conventional_total_cost": None,
        "consumer_count": consumer,
        "cloud_monthly_cost": cloud_total,
        "eeg_refund_per_kwh": float(settings["data"]["wi_settings"]["eeg_refund_per_kwh"]),
        "refund_per_kwh": settings["data"]["wi_settings"]["refund_per_kwh"],
        "pv_offer_total": float(offer.total - offer.total_tax),
        "loan_interest_rate": settings["data"]["wi_settings"]["loan_interest_rate"],
        "loan_total": None,
        "cloud_total": None,
        "cost_total": None,
        "cost_benefit": None
    }
    if offer.data is not None and "loan_total" in offer.data and offer.data["loan_total"] is not None and offer.data["loan_total"] != "":
        data["pv_offer_total"] = float(offer.data["loan_total"])
    yearly_loan_payment = (data["pv_offer_total"] * data["loan_interest_rate"] / 100) / (1 - (1 + data["loan_interest_rate"] / 100) ** -20)
    data["loan_total_interest"] = 0
    rest_loan = data["pv_offer_total"]
    for n in range(20):
        interest = rest_loan * (data["loan_interest_rate"] / 100)
        data["loan_total_interest"] = data["loan_total_interest"] + interest
        rest_loan = rest_loan + interest - yearly_loan_payment
    data["loan_total"] = data["loan_total_interest"] + data["pv_offer_total"]
    data["conventional_usage_cost"] = data["conventional_base_cost_per_kwh"] * float(data["usage"])

    base = data["conventional_usage_cost"] + data["conventional_base_cost_per_year"]
    base_base = data["conventional_base_cost_per_year"]
    base_usage = data["conventional_usage_cost"]

    data["total_pages"] = 17
    data["lightcloud"] = {
        "price_today": (data["conventional_base_cost_per_year"] + data["conventional_usage_cost"]) / 12,
        "price_tomorrow": float(cloud_calulation["cloud_price_light"]) + float(cloud_calulation["cloud_price_consumer"])
    }
    data["lightcloud"]["price_half_time"] = data["lightcloud"]["price_today"] * (1 + data["full_cost_increase_rate"] / 100) ** (data["cloud_runtime"] / 2)
    data["lightcloud"]["price_full_time"] = data["lightcloud"]["price_today"] * (1 + data["full_cost_increase_rate"] / 100) ** data["cloud_runtime"]
    if cloud_calulation["cloud_price_ecloud"] > 0:
        data["total_pages"] = data["total_pages"] + 1
        data["ecloud"] = {
            "price_today": (cloud_calulation["ecloud_usage"] * 0.0598) / 12,
            "price_tomorrow": cloud_calulation["cloud_price_ecloud"]
        }
        base = base + data["ecloud"]["price_today"] * 12
        data["ecloud"]["price_half_time"] = data["ecloud"]["price_today"] * (1 + 4.8 / 100) ** (data["cloud_runtime"] / 2)
        data["ecloud"]["price_full_time"] = data["ecloud"]["price_today"] * (1 + 4.8 / 100) ** data["cloud_runtime"]
    if cloud_calulation["cloud_price_heatcloud"] > 0:
        data["total_pages"] = data["total_pages"] + 1
        data["heatcloud"] = {
            "price_today": (cloud_calulation["heater_usage"] * 0.23) / 12,
            "price_tomorrow": cloud_calulation["cloud_price_heatcloud"]
        }
        base = base + data["heatcloud"]["price_today"] * 12
        data["heatcloud"]["price_half_time"] = data["heatcloud"]["price_today"] * (1 + 4.8 / 100) ** (data["cloud_runtime"] / 2)
        data["heatcloud"]["price_full_time"] = data["heatcloud"]["price_today"] * (1 + 4.8 / 100) ** data["cloud_runtime"]
    if cloud_calulation["cloud_price_emove"] > 0:
        data["total_pages"] = data["total_pages"] + 1
        data["emove"] = {
            "price_today": 0,
            "price_tomorrow": cloud_calulation["cloud_price_emove"]
        }
        if emove_tarif == "emove.drive I":
            data["emove"]["price_today"] = 8000 / 100 * 7 * 1.19 / 12
        if emove_tarif == "emove.drive II":
            data["emove"]["price_today"] = 12000 / 100 * 7 * 1.19 / 12
        if emove_tarif == "emove.drive III":
            data["emove"]["price_today"] = 20000 / 100 * 7 * 1.19 / 12
        if emove_tarif == "emove.drive ALL":
            data["emove"]["price_today"] = 25000 / 100 * 7 * 1.19 / 12
        base = base + data["emove"]["price_today"] * 12
        data["emove"]["price_half_time"] = data["emove"]["price_today"] * (1 + 3.95 / 100) ** (data["cloud_runtime"] / 2)
        data["emove"]["price_full_time"] = data["emove"]["price_today"] * (1 + 3.95 / 100) ** data["cloud_runtime"]

    data["conventional_total_usage_cost"] = data["conventional_usage_cost"]
    for n in range(data["runtime"]):
        data["conventional_total_usage_cost"] = data["conventional_total_usage_cost"] + data["conventional_total_usage_cost"] * ((1 + data["full_cost_increase_rate"] / 100) ** data["runtime"])

    data["conventional_total_base_cost"] = data["conventional_base_cost_per_year"]
    for n in range(data["runtime"]):
        data["conventional_total_base_cost"] = data["conventional_total_base_cost"] + data["conventional_total_base_cost"] * ((1 + data["full_cost_increase_rate"] / 100) ** data["runtime"])

    data["conventional_total_cost"] = 0
    data["conventional_total_cost_base"] = 0
    data["conventional_total_cost_usage"] = 0
    for n in range(data["runtime"]):
        data["conventional_total_cost"] = data["conventional_total_cost"] + base
        data["conventional_total_cost_base"] = data["conventional_total_cost_base"] + base_base
        data["conventional_total_cost_usage"] = data["conventional_total_cost_usage"] + base_usage
        base = base * (1 + data["full_cost_increase_rate"] / 100)
        base_base = base_base * (1 + data["full_cost_increase_rate"] / 100)
        base_usage = base_usage * (1 + data["full_cost_increase_rate"] / 100)

    insurance_cost = data["loan_total"] * 0.08
    if insurance_cost > 4500:
        insurance_cost = 4500
    # 5.88 for remote care cost
    data["cloud_total"] = (data["cloud_monthly_cost"] + 5.88) * 12 * int(cloud_runtime) \
        + ((data["cloud_monthly_cost"] + 5.88) * 12) * ((1 + data["full_cost_increase_rate"] / 100) ** (data["runtime"] - int(cloud_runtime))) \
        + insurance_cost

    data["cost_total"] = data["cloud_total"] + data["loan_total"]
    data["cost_benefit"] = data["conventional_total_cost"] - data["cost_total"]
    max_cost = (data["conventional_total_cost_base"] + data["conventional_total_cost_usage"])
    if data["cost_total"] > max_cost:
        max_cost = data["cost_total"]
    data["cost_conventional_rate"] = (data["conventional_total_cost_base"] + data["conventional_total_cost_usage"]) / max_cost
    data["cost_cloud_rate"] = data["cost_total"] / max_cost
    return data


def generate_feasibility_study_2020_pdf(offer: OfferV2):
    settings = get_settings("pv-settings")
    if settings is None:
        return None
    data = calculate_feasibility_study(offer)
    data["base_url"] = "https://api.korbacher-energiezentrum.de.ah.hbbx.de"
    content = render_template("feasibility_study_2020/index.html", offer=offer, data=data, settings=settings)
    if True:
        pdf = gotenberg_pdf(content, landscape=True, margins=[0, 0, 0, 0])
        if pdf:
            pdf_file = S3File.query\
                .filter(S3File.model == "OfferV2FeasibilityStudy")\
                .filter(S3File.model_id == offer.id)\
                .first()
            file_data = {
                "model": "OfferV2FeasibilityStudy",
                "model_id": offer.id,
                "content-type": 'application/pdf',
                "file_content": pdf,
                "filename": f"Wirtschaftlichkeitsrechnung PV-{offer.id}.pdf"
            }
            if pdf_file is not None:
                update_file(pdf_file.id, file_data)
            else:
                add_file(file_data)
            response = make_response(pdf)
            response.headers['Content-Type'] = 'application/pdf'
            return response
    response = make_response(content)
    response.headers['Content-Type'] = 'text/html'
    return response


def generate_feasibility_study_pdf(offer: OfferV2):
    if offer.reseller is not None and offer.reseller.document_style == "bsh":
        return generate_feasibility_study_2020_pdf(offer)
    settings = get_settings("pv-settings")
    if settings is None:
        return None
    data = calculate_feasibility_study(offer)

    content = render_template("feasibility_study/overlay.html", offer=offer, data=data, settings=settings)
    config = pdfkit.configuration(wkhtmltopdf="./wkhtmltopdf")
    overlay_binary = pdfkit.from_string(content, configuration=config, output_path=False, options={
        'disable-smart-shrinking': ''
    })
    if True and overlay_binary is not None:
        pdf = BytesIO()
        output = PdfFileWriter()
        base_study_pdf = PdfFileReader(open("app/modules/offer/static/feasibility_study.pdf", 'rb'))
        overlay_pdf = PdfFileReader(BytesIO(overlay_binary))
        i2 = 0
        extra_pages = 0
        extra_pages2 = 0
        extra_pages3 = 0
        for i in range(data["total_pages"]):
            if i == 7:
                page = base_study_pdf.getPage(16)
            elif i == 8 and "ecloud" in data:
                page = base_study_pdf.getPage(17)
                extra_pages = extra_pages + 1
            elif i == 8 + extra_pages and "heatcloud" in data:
                page = base_study_pdf.getPage(18)
                extra_pages2 = extra_pages2 + 1
            elif i == 8 + extra_pages + extra_pages2 and "emove" in data:
                page = base_study_pdf.getPage(19)
                extra_pages3 = extra_pages3 + 1
            else:
                page = base_study_pdf.getPage(i2)
                i2 = i2 + 1
            page.mergePage(overlay_pdf.getPage(i))
            output.addPage(page)
        output.write(pdf)
        pdf.seek(0)
        pdf_file = S3File.query\
            .filter(S3File.model == "OfferV2FeasibilityStudy")\
            .filter(S3File.model_id == offer.id)\
            .first()
        file_data = {
            "model": "OfferV2FeasibilityStudy",
            "model_id": offer.id,
            "content-type": 'application/pdf',
            "file": pdf,
            "filename": f"Wirtschaftlichkeitsrechnung PV-{offer.id}.pdf"
        }
        if pdf_file is not None:
            update_file(pdf_file.id, file_data)
        else:
            add_file(file_data)
        pdf.seek(0)
        response = make_response(pdf.read())
        response.headers['Content-Type'] = 'application/pdf'
        return response
    response = make_response(content)
    response.headers['Content-Type'] = 'text/html'
    return response
