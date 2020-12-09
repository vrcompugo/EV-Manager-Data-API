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
from app.modules.external.bitrix24.drive import get_file_content, get_file_content_cached
from app.modules.external.bitrix24.contact import get_contact
from app.modules.external.bitrix24.products import get_list as get_product_list, get_product
from app.modules.external.bitrix24._field_values import convert_field_euro_from_remote
from app.modules.cloud.services.calculation import calculate_cloud as get_cloud_calculation
from app.utils.gotenberg import gotenberg_pdf
from app.utils.jinja_filters import currencyformat, numberformat
from app.utils.pdf_form_filler import update_form_values, get_form_fields


def generate_order_confirmation_pdf(quote_id, data, return_string=False):
    config_general = get_settings(section="general")
    if data is not None:
        data["heading"] = "Auftragsbestätigung"
        data["data"] = {}
        header_content = render_template(
            "order_confirmation/generator/header.html",
            base_url=config_general["base_url"],
            quote_id=quote_id,
            data=data
        )
        footer_content = render_template(
            "order_confirmation/generator/footer.html",
            base_url=config_general["base_url"],
            quote_id=quote_id,
            data=data
        )
        content = render_template(
            "order_confirmation/generator/index.html",
            base_url=config_general["base_url"],
            quote_id=quote_id,
            data=data
        )
        if return_string:
            return content
        pdf = gotenberg_pdf(
            content,
            content_header=header_content,
            content_footer=footer_content,
            landscape=False)
        return pdf
    return None
