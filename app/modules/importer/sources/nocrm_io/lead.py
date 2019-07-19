from app import db
import pprint
import os

from app.models import Customer, Lead, S3File
from app.modules.lead.lead_services import add_item, update_item

from ._connector import post, get, put
from ._association import find_association, associate_item
from ..orgamaxx.customer import import_by_lead_number


def filter_input(item_data):
    if item_data["extended_info"]["fields_by_name"]["Interessenten-Nr."] == "":
        return None
    customer = db.session.query(Customer)\
        .filter(Customer.lead_number == str(item_data["extended_info"]["fields_by_name"]["Interessenten-Nr."]))\
        .first()
    if customer is None:
        customer = import_by_lead_number(item_data["extended_info"]["fields_by_name"]["Interessenten-Nr."])
    if customer is None:
        return None
    reseller_accociation = find_association("Reseller", remote_id=item_data["user_id"])
    if reseller_accociation is None:
        print("reseller: ", item_data["user_id"])
        return None

    data = {
        "reseller_id": reseller_accociation.local_id,
        "customer_id": customer.id,
        "value": item_data["amount"],
        "number": item_data["extended_info"]["fields_by_name"]["Interessenten-Nr."],
        "status": item_data["step"]
    }
    if customer.default_address is not None:
        data["address_id"] = customer.default_address.id
    return data


def run_import():
    pp = pprint.PrettyPrinter(indent=2)
    print("Loading Lead List")
    items = get("leads", {
        "limit": 1,
        "offset": 0,
        "order": "last_update",
        "direction": "desc",
        "step": "Neu"
    })
    for item_data in items:
        item_data = get("leads/{}".format(item_data["id"]))
        lead_association = find_association("Lead", remote_id=item_data["id"])
        if lead_association is None:
            data = filter_input(item_data)
            if data is not None:
                item = add_item(data)
                associate_item(model="Lead", local_id=item.id, remote_id=item_data["id"])
                print(data)
            else:
                print(item_data)
        else:
            data = filter_input(item_data)
            if data is not None:
                update_item(lead_association.remote_id, data)
    return False


def update_lead_by_offer(offer):
    if "pv_offer" in offer.data and "files" in offer.data["pv_offer"]:
        lead = db.session.query(Lead).filter(Lead.number == offer.customer.lead_number).first()
        if lead is not None:
            remote_link = find_association("Lead", local_id=lead.id)
            if remote_link is not None:
                put("leads/{}".format(remote_link.remote_id), post_data={
                    "amount": float(offer.data["pv_offer"]["offer_amount"])
                })
                for file in offer.data["pv_offer"]["files"]:
                    s3_file = db.session.query(S3File).get(file["id"])
                    file_link = find_association(model="LeadUpload", local_id=s3_file.id)
                    if file_link is None:
                        s3_file_content = s3_file.get_file()
                        with open("tmp/" + s3_file.filename, 'wb') as file_data:
                            for d in s3_file_content.stream(32 * 1024):
                                file_data.write(d)
                        with open("tmp/" + s3_file.filename, 'rb') as file_data:
                            response = post("leads/{}/attachments".format(remote_link.remote_id), files={"attachment": file_data})
                            associate_item(model="LeadUpload", local_id=s3_file.id, remote_id=response["id"])
                        os.remove("tmp/" + s3_file.filename)
