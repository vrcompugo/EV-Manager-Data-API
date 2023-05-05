import datetime
from io import BytesIO
import json
import math
import base64
from zipfile import ZipFile, ZipInfo

from app import db
from app.exceptions import ApiException
from app.modules.external.fakturia.invoice import get_invoices, get_invoice_document, get_invoice_corrections, get_invoice_correction_document
from app.modules.external.fakturia.credit_note import get_credit_notes, get_credit_note_document, get_credit_note_corrections, get_credit_note_correction_document
from app.modules.external.bitrix24.drive import get_public_link
from app.modules.external.bitrix24.invoice import get_invoices as get_invoices_bitrix, get_document as get_invoice_document_bitrix
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
    print(week_number)
    year = last_week_begin.year
    bundle = InvoiceBundle.query.filter(InvoiceBundle.kw == week_number).filter(InvoiceBundle.year == year).first()
    if bundle is None:
        bundle = InvoiceBundle(kw=week_number, year=year, items_count=0)
        db.session.add(bundle)
    else:
        if bundle.is_complete in [True, "true", 1] or bundle.is_running in [True, "true", 1]:
            print("nothing to do")
            return
    bundle.is_running = True
    bundle.items_count = 0
    db.session.commit()
    index = 1
    zipfile = BytesIO()
    zipfile.name = f"KW {week_number} {year} Dokumente-{index}.zip"
    zip_archive = ZipFile(zipfile, 'w')
    items = get_invoices(last_week_begin, last_week_end)
    if len(items) > 0:
        for item in items:
            zip_archive, zipfile, index = append_item(item, bundle, zip_archive, zipfile, get_invoice_document, week_number, year, index)

    items = get_invoice_corrections(last_week_begin, last_week_end)
    if len(items) > 0:
        for item in items:
            zip_archive, zipfile, index = append_item(item, bundle, zip_archive, zipfile, get_invoice_correction_document, week_number, year, index)

    items = get_credit_notes(last_week_begin, last_week_end)
    if len(items) > 0:
        for item in items:
            zip_archive, zipfile, index = append_item(item, bundle, zip_archive, zipfile, get_credit_note_document, week_number, year, index)

    items = get_credit_note_corrections(last_week_begin, last_week_end)
    if len(items) > 0:
        for item in items:
            zip_archive, zipfile, index = append_item(item, bundle, zip_archive, zipfile, get_credit_note_correction_document, week_number, year, index)

    if week_number == 5 and year == 2023:
        items = get_invoices_bitrix({}, force_reload=True)
    else:
        items = get_invoices_bitrix({
            "filter[>updatedTime]": str(last_week_begin),
            "filter[<updatedTime]": str(last_week_end)
        }, force_reload=True)
        items = items + get_invoices_bitrix({
            "filter[>createdTime]": str(last_week_begin),
            "filter[<createdTime]": str(last_week_end)
        }, force_reload=True)
    if len(items) > 0:
        for item in items:
            if item.get("stageid") != "DT31_2:UC_QL7S39":
                zip_archive, zipfile, index = append_bitrix_item(item, bundle, zip_archive, zipfile, get_invoice_document_bitrix, week_number, year, index)

    if bundle.items_count > 0:
        s3_file = upload_zipfile(zip_archive, zipfile, bundle, index)
        if s3_file is not None:
            bundle.is_complete = True
    db.session.commit()


def append_bitrix_item(item, bundle, zip_archive, zipfile, document_function, week_number, year, index):
    print(item.get("number"))
    document = document_function(item.get("id"))
    if document is None:
        return zip_archive, zipfile, index
    if zipfile.getbuffer().nbytes > 60000000:
        upload_zipfile(zip_archive, zipfile, bundle, index)
        index = index + 1
        zipfile = BytesIO()
        zipfile.name = f"KW {week_number} {year} Dokumente-{index}.zip"
        print("new_zip", zipfile.name)
        zip_archive = ZipFile(zipfile, 'w')
        print(zip_archive)

    invoice_item = InvoiceBundleItem.query.filter(InvoiceBundleItem.invoice_number == item.get("number")).first()
    if invoice_item is None:
        invoice_item = InvoiceBundleItem(invoice_number=item.get("number"))
        db.session.add(invoice_item)
    invoice_item.datetime = item.get("invoice_datetime")
    invoice_item.invoice_bundle_id = bundle.id
    invoice_item.contract_number = None
    invoice_item.customer_number = item.get("customer_number")
    invoice_item.customer_name = item.get("first_name")
    invoice_item.customer_street = item.get("street")
    invoice_item.customer_zip = item.get("zip")
    invoice_item.customer_city = item.get("city")
    invoice_item.total = item.get("opportunity")
    invoice_item.total_net = invoice_item.total - item.get("tax_value")
    invoice_item.source = "bitrix"
    db.session.commit()
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
        try:
            add_item(file_data)
        except ApiException as e:
            print("upload failed")
    else:
        # update_item(s3_file.id, file_data)
        pass
    return zip_archive, zipfile, index


def append_item(item, bundle, zip_archive, zipfile, document_function, week_number, year, index):
    print(item.get("number"))
    print(zip_archive)
    print(zipfile.getbuffer().nbytes)
    if zipfile.getbuffer().nbytes > 60000000:
        upload_zipfile(zip_archive, zipfile, bundle, index)
        index = index + 1
        zipfile = BytesIO()
        zipfile.name = f"KW {week_number} {year} Dokumente-{index}.zip"
        print("new_zip", zipfile.name)
        zip_archive = ZipFile(zipfile, 'w')
        print(zip_archive)

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
        try:
            add_item(file_data)
        except ApiException as e:
            print("upload failed")
    else:
        # update_item(s3_file.id, file_data)
        pass
    return zip_archive, zipfile, index


def upload_zipfile(zip_archive, zipfile, bundle, index):
    zip_archive.close()
    zipfile.seek(0)
    zipfile_data = {
        "model": f"invoice_bundle-{index}",
        "model_id": bundle.id,
        "filename": zipfile.name,
        "file": zipfile
    }
    s3_file = S3File.query.filter(S3File.model == "invoice_bundle").filter(S3File.model_id == bundle.id).first()
    if s3_file is None:
        try:
            s3_file = add_item(zipfile_data)
        except ApiException as e:
            try:
                s3_file = add_item(zipfile_data)
            except ApiException as e:
                bundle.is_complete = False
                bundle.is_running = False
                db.session.commit()
                raise ApiException("upload-failed", "zipfile upload failed", 500)
                print("zipfile  upload failed")
                print(zipfile)
    else:
        s3_file = update_item(s3_file.id, zipfile_data)
    return s3_file