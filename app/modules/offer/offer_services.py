import datetime
import dateutil.relativedelta
from sqlalchemy import or_
from flask import render_template, request, make_response
from PyPDF2 import PdfFileWriter, PdfFileReader
from io import StringIO, BytesIO
import pdfkit

from app import db
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict
from app.utils.gotenberg import generate_pdf
from app.models import Lead, Product, S3File, Survey, Settings
from app.modules.file.file_services import add_item as add_file, update_item as update_file

from .models.offer import Offer, OfferSchema
from .models.offer_v2 import OfferV2
from .models.offer_v2_item import OfferV2Item
from .services.offer_generation import automatic_offer_creation_by_survey
from .services.add_update_item import add_item, add_item_v2, update_item
from .services.pdf_generation.cloud_offer import generate_cloud_pdf
from .services.pdf_generation.feasibility_study import generate_feasibility_study_pdf
from .services.pdf_generation.offer import generate_offer_pdf


def get_items(tree, sort, offset, limit, fields):
    return get_items_by_model(Offer, OfferSchema, tree, sort, offset, limit, fields)


def get_one_item(id, fields=None):
    return get_one_item_by_model(Offer, OfferSchema, id, fields, [])
