import re
import json
import base64
import datetime
from dateutil.parser import parse

from app import db
from app.exceptions import ApiException
from app.models import OfferV2

from ._connector import post, put, get


def get_invoices(date_from: datetime.datetime, date_to: datetime.datetime):
    invoices = get("/Invoices", parameters={
        "dateFrom": date_from.strftime("%Y-%m-%d"),
        "dateTo": date_to.strftime("%Y-%m-%d"),
        "extendedData": "true"
    })
    return invoices


def get_invoice_document(invoice_number):
    return get(f"/Invoices/{invoice_number}/Document")


def get_invoice_corrections(date_from: datetime.datetime, date_to: datetime.datetime):
    invoices = get("/InvoiceCorrections", parameters={
        "dateFrom": date_from.strftime("%Y-%m-%d"),
        "dateTo": date_to.strftime("%Y-%m-%d"),
        "extendedData": "true"
    })
    return invoices


def get_invoice_correction_document(number):
    return get(f"/InvoiceCorrections/{number}/Document")