import pprint
from app import db
from app.modules.lead.lead_comment_services import add_item , update_item, get_one_item
from app.models import Lead
from app.modules.file.models.s3_file import S3FileSchema

from ._connector import post, get
from ._association import find_association, associate_item
from .file import run_import as run_file_import


def filter_input(data):

    item = find_association(model="Customer", remote_id=data["customer_id"])
    data["customer_id"] = item.local_id if item is not None else None
    if "customer" in data:
        del data["customer"]

    file_schema = S3FileSchema()
    attachments = []
    if "offers" in data:
        for offer in data["offers"]:
            if "pv_offer" in offer["data"] and "files" in offer["data"]["pv_offer"]:
                data["amount"] = offer["data"]["pv_offer"]["offer_amount"]
                for i in range(len(offer["data"]["pv_offer"]["files"])):
                    file = offer["data"]["pv_offer"]["files"][i]
                    local_file = run_file_import("Offer", model_id=None, id=file["id"])
                    attachments.append(file_schema.dump(local_file, many=False).data)
            else:
                local_file = run_file_import("OfferPDF", 0, offer["id"])
                if local_file is not None:
                    attachments.append(file_schema.dump(local_file, many=False).data)
        del data["offers"]

    lead = db.session.query(Lead).filter(Lead.number == data["lead_number"]).first()
    if lead is None:
        return None
    data["lead_id"] = lead.id
    lead.value = float(data["amount"])
    db.session.commit()

    if "customer_files" in data:
        for customer_file in data["customer_files"]:
            local_file = run_file_import("Customer", data["customer_id"], customer_file["id"])
            if local_file is not None:
                attachments.append(file_schema.dump(local_file, many=False).data)
        del data["customer_files"]

    if "pv_files" in data:
        for pv_file in data["pv_files"]:
            local_file = run_file_import("PVFile", 0, pv_file["id"])
            if local_file is not None:
                attachments.append(file_schema.dump(local_file, many=False).data)
        del data["pv_files"]
    data["attachments"] = attachments

    data["comment"] = data["full_comment"]

    return data


def run_import(remote_id=None, local_id=None):
    if remote_id is not None:
        item_data = get("LeadComment/{}".format(remote_id))["item"]
        if item_data is not None:
            import_item(item_data)
        return
    data = post("LeadComment", {"page": 0, "limit": 1000})
    if "items" in data:
        for item_data in data["items"]:
            import_item(item_data)

    return False


def import_item(item_data):

    item_data = filter_input(item_data)

    item = find_association(model="LeadComment", remote_id=item_data["id"])
    if item is None:
        item = add_item(item_data)
        if item is not None:
            associate_item(model="LeadComment", remote_id=item_data["id"], local_id=item.id)
    else:
        item = update_item(id=item.local_id, data=item_data)
    return item
