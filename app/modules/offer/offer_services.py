import datetime
from sqlalchemy import or_
from flask import render_template, request, make_response

from app import db
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict
from app.utils.gotenberg import generate_pdf
from app.models import Lead, Product, S3File
from app.modules.file.file_services import add_item as add_file, update_item as update_file

from .models.offer import Offer, OfferSchema
from .models.offer_v2 import OfferV2
from .models.offer_v2_item import OfferV2Item


def add_item(data):
    new_item = Offer()
    new_item = set_attr_by_dict(new_item, data, ["id"])
    new_item.last_updated = datetime.datetime.now()
    db.session.add(new_item)
    db.session.commit()
    return new_item


def update_item(id, data):
    item = db.session.query(Offer).get(id)
    if item is not None:
        item = set_attr_by_dict(item, data, ["id"])
        db.session.commit()
        return item
    else:
        raise ApiException("item_doesnt_exist", "Item doesn't exist.", 409)


def add_item_v2(data):
    new_item = OfferV2()
    new_item = set_attr_by_dict(new_item, data, ["id", "items"])
    if "items" in data:
        new_item.items = []
        for item_data in data["items"]:
            item_object = OfferV2Item()
            item_object = set_attr_by_dict(item_object, item_data, ["id"])
            new_item.items.append(item_object)
    new_item.last_updated = datetime.datetime.now()
    db.session.add(new_item)
    db.session.commit()
    # loading relations for pdf creation
    customer = new_item.customer
    items = new_item.items
    address = new_item.address
    generate_offer_pdf(new_item)
    return new_item


def get_items(tree, sort, offset, limit, fields):
    return get_items_by_model(Offer, OfferSchema, tree, sort, offset, limit, fields)


def get_one_item(id, fields=None):
    return get_one_item_by_model(Offer, OfferSchema, id, fields, [])


def automatic_offer_creation_by_survey(survey, old_data=None):

    from app.modules.importer.sources.bitrix24.offer import run_export
    from app.modules.importer.sources.bitrix24.lead import run_status_update_export

    if ("offer_comment" not in survey.data or survey.data["offer_comment"] == "") and \
            survey.data["pv_usage"] is not None and \
            survey.data["pv_usage"] != "" and \
            int(survey.data["pv_usage"]) > 0 and \
            (old_data is None or survey.data["pv_usage"] != old_data["data"]["pv_usage"]):

        offer_data = {
            "customer_id": survey.customer_id,
            "address_id": survey.customer.default_address_id,
            "payment_account_id": survey.customer.default_payment_account_id,
            "reseller_id": survey.reseller_id,
            "survey_id": survey.id,
            "offer_group": "pv-offer",
            "datetime": datetime.datetime.now(),
            "currency": "eur",
            "tax_rate": 19,
            "subtotal": 0,
            "subtotal_net": 0,
            "shipping_cost": 0,
            "shipping_cost_net": 0,
            "discount_total": 0,
            "total_tax": 0,
            "total": 0,
            "status": "created",
            "items": []
        }

        product_name = "PV Paket {}".format(survey.data["packet_number"])
        if survey.data["pv_module_type"] == "390":
            product_name = "PV Paket {} (390)".format(survey.data["packet_number"])
        if survey.data["pv_module_type"] == "400":
            product_name = "PV Paket {} (400)".format(survey.data["packet_number"])

        offer_data = add_item_to_offer(offer_data, product_name, 1)

        if int(survey.data["packet_number"]) >= 35:
            quantity = 1
            if 65 <= int(survey.data["packet_number"]) <= 70:
                quantity = 2
            if 75 <= int(survey.data["packet_number"]) <= 85:
                quantity = 3
            if 90 <= int(survey.data["packet_number"]) <= 125:
                quantity = 4
            if 130 <= int(survey.data["packet_number"]) <= 155:
                quantity = 5
            if 160 <= int(survey.data["packet_number"]) <= 180:
                quantity = 6
            if 185 <= int(survey.data["packet_number"]) <= 220:
                quantity = 7
            if 230 <= int(survey.data["packet_number"]) <= 300:
                quantity = 9
            offer_data = add_item_to_offer(offer_data, "Akku Stag 2,5 kW", quantity)

        offer_data = add_item_to_offer(offer_data, "Wechselrichter & Optimizer", 0)
        offer_data = add_item_to_offer(offer_data, "Neuer Zählerschrank inkl. Montage", 0)
        offer_data = add_item_to_offer(offer_data, "WaLLbox  400V 11kW", 0)
        offer_data = add_item_to_offer(offer_data, "ecoSTAR taglio 100", 0)
        offer_data = add_item_to_offer(offer_data, "Technik & Service Paket", 0)
        offer_data = add_item_to_offer(offer_data, "ZERO-Paket", 0)

        if int(survey.data["packet_number"]) >= 60:
            offer_data = add_item_to_offer(offer_data, "zus. digitaler Zähler", 1)

        lead = Lead.query.filter(Lead.customer_id == survey.customer.id).first()
        if lead is not None:
            offer_data["lead_id"] = lead.id
        offer = add_item_v2(offer_data)
        run_export(local_id=offer.id)
        if lead is not None:
            lead.value = offer.total
            lead.status = "offer_created"
            db.session.add(lead)
            db.session.commit()
            run_status_update_export(local_id=lead.id)


def add_item_to_offer(offer_data, product_name, quantity):
    product = Product.query\
        .filter(Product.name == product_name)\
        .filter(Product.product_group.like("%Erneuerbare Energie - %"))\
        .first()
    if product is None:
        raise Exception("Product not found: {}".format(product_name))
    tax_rate = 19
    single_price = round(float(product.price_net) * (1 + tax_rate / 100), 4)
    single_price_net = float(product.price_net)
    single_tax_amount = single_price - single_price_net
    item_data = {
        "product_id": product.id,
        "sort": 0,
        "number": product.number,
        "label": product.name,
        "description": product.description,
        "quantity_unit": product.pack_unit,
        "weight_single": 0,
        "weight_total": 0,
        "quantity": quantity,
        "cost": 0,
        "tax_rate": 19,
        "single_price": single_price,
        "single_price_net": single_price_net,
        "single_tax_amount": single_tax_amount,
        "discount_rate": 0,
        "discount_single_amount": 0,
        "discount_single_price": single_price,
        "discount_single_price_net": single_price_net,
        "discount_single_tax_amount": single_tax_amount,
        "total_price": quantity * single_price,
        "total_price_net": quantity * single_price_net,
        "total_tax_amount": quantity * single_tax_amount
    }
    offer_data["subtotal"] = offer_data["subtotal"] + item_data["total_price"]
    offer_data["subtotal_net"] = offer_data["subtotal_net"] + item_data["total_price_net"]
    offer_data["total_tax"] = offer_data["total_tax"] + item_data["total_tax_amount"]
    offer_data["total"] = offer_data["total"] + item_data["total_price"]
    offer_data["items"].append(item_data)
    return offer_data


def generate_offer_pdf(offer: OfferV2):
    content = render_template("offer/index.html", offer=offer)
    content_footer = render_template("offer/footer.html", offer=offer)
    pdf = generate_pdf(content, content_footer=content_footer)
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
            "filename": f"Angebot PV-{offer.id}.pdf"
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
