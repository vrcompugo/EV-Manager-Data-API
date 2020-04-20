
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
    items = cloud_offer_items_by_pv_offer(offer)
    cloud_total = 0
    for item in items:
        cloud_total = cloud_total + float(item["total_price"])
    in_use_date = offer.datetime + dateutil.relativedelta.relativedelta(months=1)
    data = {
        "runtime": 30,
        "usage": float(offer.survey.data["pv_usage"]),
        "paket": int(offer.survey.data["packet_number"]),
        "orientation": offer.survey.data["roof_datas"][0]["direction"],
        "orientation_label": "Süd" if offer.survey.data["roof_datas"][0]["direction"] == "south" else "West/Ost",
        "in_use_date": in_use_date,
        "conventional_base_cost_per_year": settings["data"]["wi_settings"]["conventional_base_cost_per_year"],
        "conventional_base_cost_per_kwh": settings["data"]["wi_settings"]["conventional_base_cost_per_kwh"],
        "cost_increase_rate": settings["data"]["wi_settings"]["conventional_base_cost_per_kwh"],
        "conventional_total_cost": None,
        "consumer_count": 1,
        "cloud_monthly_cost": cloud_total,
        "eeg_refund_per_kwh": 0.1018,
        "refund_per_kwh": 0.04,
        "pv_offer_total": offer.total,
        "loan_interest_rate": 2,
        "loan_total": None,
        "cloud_total": None,
        "cost_total": None,
        "cost_benefit": None
    }
    yearly_loan_payment = (float(offer.total) * data["loan_interest_rate"] / 100) / (1 - (1 + data["loan_interest_rate"] / 100) ** -20)
    data["loan_total_interest"] = 0
    rest_loan = float(offer.total)
    for n in range(20):
        interest = rest_loan * (data["loan_interest_rate"] / 100)
        data["loan_total_interest"] = data["loan_total_interest"] + interest
        rest_loan = rest_loan + interest - yearly_loan_payment
    data["loan_total"] = data["loan_total_interest"] + float(offer.total)
    data["conventional_usage_cost"] = data["conventional_base_cost_per_kwh"] * float(data["usage"])

    data["conventional_total_usage_cost"] = data["conventional_usage_cost"]
    for n in range(data["runtime"]):
        data["conventional_total_usage_cost"] = data["conventional_total_usage_cost"] + data["conventional_total_usage_cost"] * ((1 + data["cost_increase_rate"] / 100) ** data["runtime"])

    data["conventional_total_base_cost"] = data["conventional_base_cost_per_year"]
    for n in range(data["runtime"]):
        data["conventional_total_base_cost"] = data["conventional_total_base_cost"] + data["conventional_total_base_cost"] * ((1 + data["cost_increase_rate"] / 100) ** data["runtime"])

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
        base = base * (1 + data["cost_increase_rate"] / 100)
        base_base = base_base * (1 + data["cost_increase_rate"] / 100)
        base_usage = base_usage * (1 + data["cost_increase_rate"] / 100)

    data["cloud_total"] = data["cloud_monthly_cost"] * 12 * 10 \
        + (data["cloud_monthly_cost"] * 12) * ((1 + data["cost_increase_rate"] / 100) ** (data["runtime"] - 10))
    if data["runtime"] == 20:
        data["cloud_total"] = data["cloud_total"] + 1500
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
    content = render_template("feasibility_study/overlay.html", offer=offer, data=data)
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
