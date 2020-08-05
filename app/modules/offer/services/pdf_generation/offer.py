import pdfkit
from flask import render_template, request, make_response
from PyPDF2 import PdfFileWriter, PdfFileReader
from io import StringIO, BytesIO

from app.models import OfferV2, S3File
from app.modules.file.file_services import add_item as add_file, update_item as update_file
from app.utils.gotenberg import generate_pdf

from ..offer_generation.cloud_offer import cloud_offer_items_by_pv_offer


def generate_offer_pdf(offer: OfferV2):
    offer_number_prefix = offer.number_prefix
    if offer.offer_group == "heater-offer-con":
        offer.total_15years = float(offer.total) * 12 * 15
    content = render_template("offer/index.html", offer=offer, items=offer.items, offer_number_prefix=offer_number_prefix)
    content_footer = render_template("offer/footer.html", offer=offer, offer_number_prefix=offer_number_prefix)

    pdf = generate_pdf(content, content_footer=content_footer, margins=["0.3", "0.3", "1.6", "0.3"])
    if pdf is not None:
        pdf_file = S3File.query\
            .filter(S3File.model == "OfferV2")\
            .filter(S3File.model_id == offer.id)\
            .first()
        file_data = {
            "model": "OfferV2",
            "model_id": offer.id,
            "content-type": 'application/pdf',
            "file_content": pdf,
            "filename": f"Angebot {offer_number_prefix}{offer.id}.pdf"
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
