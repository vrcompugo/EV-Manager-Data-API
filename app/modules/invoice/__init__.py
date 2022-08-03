import datetime
from io import BytesIO
import json
import base64
from zipfile import ZipFile, ZipInfo

from app import db
from app.modules.external.fakturia.invoice import get_invoices, get_invoice_document, get_invoice_corrections, get_invoice_correction_document
from app.modules.external.fakturia.credit_note import get_credit_notes, get_credit_note_document, get_credit_note_corrections, get_credit_note_correction_document
from app.modules.external.bitrix24.drive import get_public_link
from app.modules.file.file_services import add_item, update_item
from app.models import S3File

from .models.invoice_bundle import InvoiceBundle
from .models.invoice_bundle_item import InvoiceBundleItem


def cron_generate_weekly_invoice_bundles(offset_weeks=0):
    print("cron_generate_weekly_invoice_bundles")
    now = datetime.datetime.now() - datetime.timedelta(weeks=offset_weeks)
    last_week_monday = now - datetime.timedelta(days=now.weekday() + 7)
    last_week_begin = datetime.datetime(last_week_monday.year, last_week_monday.month, last_week_monday.day)
    last_week_end = last_week_begin + datetime.timedelta(days=6, hours=23, minutes=59, seconds=59)
    week_number = last_week_begin.isocalendar()[1]
    year = last_week_begin.year
    bundle = InvoiceBundle.query.filter(InvoiceBundle.kw == week_number).filter(InvoiceBundle.year == year).first()
    if bundle is None:
        bundle = InvoiceBundle(kw=week_number, year=year, items_count=0)
        db.session.add(bundle)
        db.session.flush()
    else:
        print("nothing to do")
        return
    bundle.items_count = 0
    zipfile = BytesIO()
    zipfile.name = f"KW {week_number} {year} Dokumente.zip"
    with ZipFile(zipfile, 'w') as zip_archive:
        print(last_week_begin, last_week_end)
        items = get_invoices(last_week_begin, last_week_end)
        print("2")
        if len(items) > 0:
            for item in items:
                append_item(item, bundle, zip_archive, get_invoice_document)

        items = get_invoice_corrections(last_week_begin, last_week_end)
        if len(items) > 0:
            for item in items:
                append_item(item, bundle, zip_archive, get_invoice_correction_document)

        items = get_credit_notes(last_week_begin, last_week_end)
        if len(items) > 0:
            for item in items:
                append_item(item, bundle, zip_archive, get_credit_note_document)

        items = get_credit_note_corrections(last_week_begin, last_week_end)
        if len(items) > 0:
            for item in items:
                append_item(item, bundle, zip_archive, get_credit_note_correction_document)

    if bundle.items_count > 0:
        zipfile.seek(0)
        zipfile_data = {
            "model": "invoice_bundle",
            "model_id": bundle.id,
            "filename": zipfile.name,
            "file": zipfile
        }
        s3_file = S3File.query.filter(S3File.model == "invoice_bundle").filter(S3File.model_id == bundle.id).first()
        if s3_file is None:
            s3_file = add_item(zipfile_data)
        else:
            s3_file = update_item(s3_file.id, zipfile_data)
        bundle.download_link = get_public_link(s3_file.bitrix_file_id, 172800)
    db.session.commit()
    #invoice corrections

def append_item(item, bundle, zip_archive, document_function):
    print(item.get("number"))
    invoice_item = InvoiceBundleItem.query.filter(InvoiceBundleItem.invoice_number == item.get("number")).first()
    if invoice_item is None:
        invoice_item = InvoiceBundleItem(invoice_number=item.get("number"))
        db.session.add(invoice_item)
    invoice_item.datetime = item.get("date")
    invoice_item.invoice_bundle_id = bundle.id
    invoice_item.contract_number = item.get("contractNumber")
    invoice_item.customer_number = item.get("customerNumber")
    invoice_item.customer_name = item.get("customerName1")
    invoice_item.customer_street = item.get("addressLine1")
    invoice_item.customer_zip = item.get("zipCode")
    invoice_item.customer_city = item.get("city")
    invoice_item.total_net = item.get("amountNet")
    invoice_item.total = item.get("amountGross")
    invoice_item.source = "fakturia"
    db.session.commit()
    document = document_function(item.get("number"))
    document = base64.b64decode(document.get("document"))
    zip_archive.writestr(f'{item.get("number")}.pdf', document)
    bundle.items_count = bundle.items_count + 1
    file_data = {
        "model": "invoice_bundle_item",
        "model_id": invoice_item.id,
        "filename": f'{item.get("number")}.pdf',
        "file_content": document
    }
    s3_file = S3File.query.filter(S3File.model == "invoice_bundle_item").filter(S3File.model_id == invoice_item.id).first()
    if s3_file is None:
        add_item(file_data)
    else:
        # update_item(s3_file.id, file_data)
        pass
