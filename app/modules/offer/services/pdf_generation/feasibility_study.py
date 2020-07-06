
import pdfkit
from flask import render_template, request, make_response
from PyPDF2 import PdfFileWriter, PdfFileReader
from io import StringIO, BytesIO
import dateutil

from app.modules.settings.settings_services import get_one_item as get_settings
from app.modules.file.file_services import add_item as add_file, update_item as update_file
from app.models import OfferV2, S3File

from ..offer_generation.cloud_offer import cloud_offer_items_by_pv_offer


def generate_feasibility_study_pdf(offer: OfferV2):

    settings = get_settings("pv-settings")
    if settings is None:
        return None
    in_use_date = offer.datetime + dateutil.relativedelta.relativedelta(months=1)
    if offer.offer_group == "cloud-offer":
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
    else:
        cloud_total = 0
        items = cloud_offer_items_by_pv_offer(offer)
        for item in items:
            cloud_total = cloud_total + float(item["total_price"])
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
        "runtime": run_time,
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
    yearly_loan_payment = (data["pv_offer_total"] * data["loan_interest_rate"] / 100) / (1 - (1 + data["loan_interest_rate"] / 100) ** -20)
    data["loan_total_interest"] = 0
    rest_loan = data["pv_offer_total"]
    for n in range(20):
        interest = rest_loan * (data["loan_interest_rate"] / 100)
        data["loan_total_interest"] = data["loan_total_interest"] + interest
        rest_loan = rest_loan + interest - yearly_loan_payment
    data["loan_total"] = data["loan_total_interest"] + data["pv_offer_total"]
    data["conventional_usage_cost"] = data["conventional_base_cost_per_kwh"] * float(data["usage"])

    data["conventional_total_usage_cost"] = data["conventional_usage_cost"]
    for n in range(data["runtime"]):
        data["conventional_total_usage_cost"] = data["conventional_total_usage_cost"] + data["conventional_total_usage_cost"] * ((1 + data["full_cost_increase_rate"] / 100) ** data["runtime"])

    data["conventional_total_base_cost"] = data["conventional_base_cost_per_year"]
    for n in range(data["runtime"]):
        data["conventional_total_base_cost"] = data["conventional_total_base_cost"] + data["conventional_total_base_cost"] * ((1 + data["full_cost_increase_rate"] / 100) ** data["runtime"])

    data["conventional_total_cost"] = 0
    data["conventional_total_cost_base"] = 0
    data["conventional_total_cost_usage"] = 0
    base = data["conventional_usage_cost"] + data["conventional_base_cost_per_year"]
    base_base = data["conventional_base_cost_per_year"]
    base_usage = data["conventional_usage_cost"]
    for n in range(data["runtime"]):
        data["conventional_total_cost"] = data["conventional_total_cost"] + base
        data["conventional_total_cost_base"] = data["conventional_total_cost_base"] + base_base
        data["conventional_total_cost_usage"] = data["conventional_total_cost_usage"] + base_usage
        base = base * (1 + data["full_cost_increase_rate"] / 100)
        base_base = base_base * (1 + data["full_cost_increase_rate"] / 100)
        base_usage = base_usage * (1 + data["full_cost_increase_rate"] / 100)

    data["cloud_total"] = data["cloud_monthly_cost"] * 12 * 10 \
        + (data["cloud_monthly_cost"] * 12) * ((1 + data["full_cost_increase_rate"] / 100) ** (data["runtime"] - 10))
    if data["runtime"] == 20:
        data["cloud_total"] = data["cloud_total"] + 1500
    if data["runtime"] == 25:
        data["cloud_total"] = data["cloud_total"] + 2000
    if data["runtime"] >= 30:
        data["cloud_total"] = data["cloud_total"] + 2500
    data["cost_total"] = data["cloud_total"] + data["loan_total"]
    data["cost_benefit"] = data["conventional_total_cost"] - data["cost_total"]
    max_cost = data["conventional_total_cost"]
    if data["cost_total"] > max_cost:
        max_cost = data["cost_total"]
    data["cost_conventional_rate"] = data["conventional_total_cost"] / max_cost
    data["cost_cloud_rate"] = data["cost_total"] / max_cost
    data["total_pages"] = 17
    content = render_template("feasibility_study/overlay.html", offer=offer, data=data, settings=settings)
    config = pdfkit.configuration(wkhtmltopdf="./wkhtmltopdf")
    overlay_binary = pdfkit.from_string(content, configuration=config, output_path=False, options={
        'disable-smart-shrinking': ''
    })
    if overlay_binary is not None:
        pdf = BytesIO()
        output = PdfFileWriter()
        base_study_pdf = PdfFileReader(open("app/modules/offer/static/feasibility_study.pdf", 'rb'))
        overlay_pdf = PdfFileReader(BytesIO(overlay_binary))
        for i in range(base_study_pdf.getNumPages()):
            page = base_study_pdf.getPage(i)
            if i < overlay_pdf.getNumPages():
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
