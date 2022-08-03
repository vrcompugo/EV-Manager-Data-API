import re
import json
import base64
import datetime
from dateutil.parser import parse

from app import db
from app.exceptions import ApiException
from app.models import OfferV2

from ._connector import post, put, get


def get_credit_notes(date_from: datetime.datetime, date_to: datetime.datetime):
    credit_notes = get("/CreditNotes", parameters={
        "dateFrom": date_from.strftime("%Y-%m-%d"),
        "dateTo": date_to.strftime("%Y-%m-%d"),
        "extendedData": "true"
    })
    return credit_notes


def get_credit_note_document(number):
    return get(f"/CreditNotes/{number}/Document")


def get_credit_note_corrections(date_from: datetime.datetime, date_to: datetime.datetime):
    credit_notes = get("/CreditNoteCorrections", parameters={
        "dateFrom": date_from.strftime("%Y-%m-%d"),
        "dateTo": date_to.strftime("%Y-%m-%d"),
        "extendedData": "true"
    })
    return credit_notes


def get_credit_note_correction_document(number):
    return get(f"/CreditNoteCorrections/{number}/Document")