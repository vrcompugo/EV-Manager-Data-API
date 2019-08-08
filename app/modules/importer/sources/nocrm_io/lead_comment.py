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

    status = "new"
    if item_data["step"] == "Kontaktiert":
        status = "contacted"
    if item_data["step"] == "Analyse durchgeführt":
        status = "survey_created"
    if item_data["step"] == "Angebot erstellt":
        status = "offer_created"
    if item_data["step"] == "Angebot präsentiert":
        status = "offer_presented"
    if item_data["step"] == "Vertragsverhandlung":
        status = "offer_negotiation"
    if item_data["step"] == "Verloren":
        status = "lost"
    if item_data["step"] == "Verkauft":
        status = "won"

    data = {
        "datetime": item_data["created_at"],
        "last_update": item_data["updated_at"],
        "reminder_datetime": item_data["reminder_at"],
        "reseller_id": reseller_accociation.local_id,
        "customer_id": customer.id,
        "value": item_data["amount"],
        "number": item_data["extended_info"]["fields_by_name"]["Interessenten-Nr."],
        "status": status,
        "data": item_data["extended_info"]["fields_by_name"],
        "description": item_data["description"],
        "description_html": item_data["html_description"]
    }
    if customer.default_address is not None:
        data["address_id"] = customer.default_address.id
    return data


def run_import():
    print("Loading Lead List")
    load_more = True
    offset = 0
    limit = 100
    while load_more:
        items = get("leads", {
            "limit": limit,
            "offset": offset,
            "order": "last_update",
            "direction": "desc"
        })
        load_more = len(items) == limit
        offset = offset + limit
        print("Count: ", len(items))
        print("Offset: ", offset)
        for item_data in items:
            item_data = get("leads/{}".format(item_data["id"]))
            lead_association = find_association("Lead", remote_id=item_data["id"])
            if lead_association is None:
                data = filter_input(item_data)
                if data is not None:
                    item = add_item(data)
                    associate_item(model="Lead", local_id=item.id, remote_id=item_data["id"])
                    print(item.id)
                else:
                    pass
                    #print(item_data["extended_info"]["fields_by_name"]["Interessenten-Nr."], item_data["user_id"], item_data["extended_info"]["user"]["email"])
            else:
                data = filter_input(item_data)
                if data is not None:
                    update_item(lead_association.local_id, data)
    return False


def update_lead_comment(lead_comment):
    print("update lead", lead_comment)
    remote_link = find_association("Lead", local_id=lead_comment.lead_id)
    if remote_link is not None:
        lead_data = {
            "amount": float(lead_comment.lead.value)
        }
        if lead_comment.change_to_offer_created:
            lead_data["step"] = "Angebot erstellt"
        response = put("leads/{}".format(remote_link.remote_id), post_data=lead_data)
        attachment_list = []
        for file in lead_comment.attachments:
            s3_file = db.session.query(S3File).get(file["id"])
            s3_file_content = s3_file.get_file()
            with open("tmp/" + s3_file.filename, 'wb') as file_data:
                for d in s3_file_content.stream(32 * 1024):
                    file_data.write(d)
            attachment_list.append(("attachments[]", (s3_file.filename, open("tmp/" + s3_file.filename, 'rb'))))

        response = post("leads/{}/comments".format(remote_link.remote_id), post_data={
            "user_id": 40297,
            "content": lead_comment.comment
        }, files=attachment_list)
        for file in lead_comment.attachments:
            s3_file = db.session.query(S3File).get(file["id"])
            if os.path.exists("tmp/" + s3_file.filename):
                os.remove("tmp/" + s3_file.filename)
        return response
