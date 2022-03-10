import datetime
import json
from flask import request
from flask_restplus import Resource
from flask_restplus import Namespace, fields

from app.exceptions import ApiException
from app.decorators import token_required, api_response
from app.modules.auth.auth_services import get_logged_in_user
from app.modules.offer.offer_services import add_item_v2, update_item_v2, get_one_item_v2
from app.modules.customer.services.customer_address_services import get_one_item as get_address_data
from app.models import OfferV2, Reseller

from .services.offer import get_offer_by_offer_number
from .services.calculation import calculate_cloud, get_cloud_products


api = Namespace('Cloud')


@api.route('/calculation')
class Items(Resource):

    @api_response
    @token_required("cloud_calculation")
    def post(self):
        """ Stores new offer """
        data = request.json
        calculated = calculate_cloud(data)
        if calculated is None:
            raise ApiException("error-calculating", "Error Calculating", 500)
        return {"status": "success",
                "data": calculated}


@api.route('/offer')
class Items(Resource):

    @api_response
    @token_required("cloud_calculation")
    def post(self):
        from app.modules.offer.services.pdf_generation.feasibility_study import generate_feasibility_study_pdf, generate_feasibility_study_short_pdf

        data = request.json
        user = get_logged_in_user()
        reseller = Reseller.query.filter(Reseller.user_id == user["id"]).first()
        if reseller is not None:
            data["document_style"] = reseller.document_style
        calculated = calculate_cloud(data)
        if calculated is None:
            raise ApiException("error-calculating", "Error Calculating", 500)
        items = get_cloud_products(data={"calculated": calculated, "data": data})
        offer_v2_data = {
            "reseller_id": None,
            "offer_group": "cloud-offer",
            "datetime": datetime.datetime.now(),
            "currency": "eur",
            "tax_rate": 19,
            "subtotal": calculated["cloud_price"],
            "subtotal_net": calculated["cloud_price"] / 1.19,
            "shipping_cost": 0,
            "shipping_cost_net": 0,
            "discount_total": 0,
            "total_tax": calculated["cloud_price"] * 0.19,
            "total": calculated["cloud_price"],
            "status": "created",
            "data": data,
            "calculated": calculated,
            "items": items,
            "customer_raw": {}
        }
        if "email" in data:
            offer_v2_data["customer_raw"]["email"] = data["email"]
        if "phone" in data:
            offer_v2_data["customer_raw"]["phone"] = data["phone"]
        if "address" in data and "lastname" in data["address"]:
            offer_v2_data["customer_raw"]["firstname"] = data["address"]["firstname"]
            offer_v2_data["customer_raw"]["lastname"] = data["address"]["lastname"]
            offer_v2_data["customer_raw"]["default_address"] = data["address"]
            if "company" in data["address"]:
                offer_v2_data["customer_raw"]["company"] = data["address"]["company"]
        if reseller is not None:
            offer_v2_data["reseller_id"] = reseller.id
        item = add_item_v2(data=offer_v2_data)
        item_dict = get_one_item_v2(item.id)
        if item.pdf is not None:
            item_dict["pdf_link"] = item.pdf.public_link
        if "create_all_pdfs" in data and data["create_all_pdfs"] is True:
            generate_feasibility_study_pdf(item)
            if item.feasibility_study_pdf is not None:
                item_dict["pdf_wi_link"] = item.feasibility_study_pdf.public_link
            generate_feasibility_study_short_pdf(item)
            if item.feasibility_study_short_pdf is not None:
                item_dict["pdf_wi_short_link"] = item.feasibility_study_short_pdf.public_link
        return {"status": "success",
                "data": item_dict}


@api.route('/offer/<offer_number>')
class User(Resource):
    @api_response
    @token_required("cloud_calculation")
    def get(self, offer_number):
        """get a contract given its identifier"""
        fields = request.args.get("fields") or "_default_"
        offer = get_offer_by_offer_number(offer_number)
        if offer is None:
            api.abort(404)
        item_dict = get_one_item_v2(offer.id, fields)
        if item_dict is None:
            api.abort(404)
        if "data" in item_dict:
            for consumer in item_dict["data"].get("consumers", []):
                if "address" not in consumer:
                    consumer["address"] = {}
        item_dict["address"] = {}
        if offer.address_id is not None and offer.address_id > 0:
            item_dict["address"] = get_address_data(offer.address_id)
        if offer.pdf is not None:
            item_dict["pdf_link"] = offer.pdf.public_link
        if offer.feasibility_study_pdf is not None:
            item_dict["pdf_wi_link"] = offer.feasibility_study_pdf.public_link
        if offer.feasibility_study_short_pdf is not None:
            item_dict["pdf_wi_short_link"] = offer.feasibility_study_short_pdf.public_link
        return {
            "status": "success",
            "data": item_dict
        }

    @api_response
    @token_required("cloud_calculation")
    def put(self, offer_number):
        from app.modules.offer.services.pdf_generation.offer import generate_offer_pdf
        from app.modules.offer.services.pdf_generation.feasibility_study import generate_feasibility_study_pdf, generate_feasibility_study_short_pdf

        offer = get_offer_by_offer_number(offer_number)
        if offer is None:
            api.abort(404)
        offer.tax_rate = 19
        data = request.json
        user = get_logged_in_user()
        reseller = Reseller.query.filter(Reseller.user_id == user["id"]).first()
        if reseller is not None:
            data["document_style"] = reseller.document_style
        calculated = calculate_cloud(data)
        if calculated is None:
            raise ApiException("error-calculating", "Error Calculating", 500)
        items = get_cloud_products(data={
            "data": data,
            "calculated": calculated
        })
        if "loan_total" in data:
            if data["loan_total"] is None or data["loan_total"] == "":
                del data["loan_total"]
        offer_v2_data = {
            "tax_rate": 19,
            "datetime": datetime.datetime.now(),
            "subtotal": calculated["cloud_price"],
            "subtotal_net": calculated["cloud_price"] / 1.19,
            "total_tax": calculated["cloud_price"] * 0.19,
            "total": calculated["cloud_price"],
            "data": data,
            "calculated": calculated,
            "items": items,
            "customer_raw": {}
        }
        if "email" in data:
            offer_v2_data["customer_raw"]["email"] = data["email"]
        if "phone" in data:
            offer_v2_data["customer_raw"]["phone"] = data["phone"]
        if "address" in data and "lastname" in data["address"]:
            offer_v2_data["customer_raw"]["firstname"] = data["address"]["firstname"]
            offer_v2_data["customer_raw"]["lastname"] = data["address"]["lastname"]
            offer_v2_data["customer_raw"]["default_address"] = data["address"]
            if "company" in data["address"]:
                offer_v2_data["customer_raw"]["company"] = data["address"]["company"]
        item = update_item_v2(id=offer.id, data=offer_v2_data)
        generate_offer_pdf(item)
        generate_feasibility_study_pdf(item)
        generate_feasibility_study_short_pdf(item)
        item_dict = get_one_item_v2(item.id)
        if item.pdf is not None:
            item_dict["pdf_link"] = item.pdf.public_link
        if item.feasibility_study_pdf is not None:
            item_dict["pdf_wi_link"] = item.feasibility_study_pdf.public_link
        if item.feasibility_study_short_pdf is not None:
            item_dict["pdf_wi_short_link"] = item.feasibility_study_short_pdf.public_link
        return {"status": "success",
                "data": item_dict}


@api.route('/offer/<offer_number>/upload')
class OfferUpload(Resource):

    @api_response
    @token_required("cloud_calculation")
    def post(self, offer_number):
        from app.modules.importer.sources.bitrix24.drive import add_file

        fileinfos = [
            {
                "key": "cloud_config",
                "label": "Cloud Konfiguration"
            },
            {
                "key": "signed_offer_pdf",
                "label": "Unterschriebenes Angebot"
            },
            {
                "key": "refund_transfer_pdf",
                "label": "Unterschriebene Abtrettungserklärung"
            },
            {
                "key": "sepa_form",
                "label": "Unterschriebene SEPA-Formular"
            },
            {
                "key": "old_power_invoice",
                "label": "Alte Stromabrechnung"
            },
            {
                "key": "old_gas_invoice",
                "label": "Alte Gas-Abrechnung"
            }
        ]
        allowed_file_list = [".pdf", ".jpg", "jpeg", ".png"]

        result_data = {}
        for fileinfo in fileinfos:
            if fileinfo["key"] not in request.files:
                continue
            file = request.files[fileinfo["key"]]
            if file.filename[-4:].lower() not in allowed_file_list:
                raise ApiException("upload-failed", "upload failed", 415)
            file_ending = file.filename[-4:].lower()
            if file_ending == "jpeg":
                file_ending = "." + file_ending
            file_id = add_file({
                "foldername": f"Angebotsdateien {offer_number}",
                "filename": f"{fileinfo['label']}{file_ending}",
                "file_content": file.read()
            })
            if file_id is None:
                raise ApiException("upload-failed", "upload failed", 418)
            result_data[f"{fileinfo['key']}_id"] = int(file_id)
        return {"status": "success",
                "data": result_data}


@api.route('/order')
class OrderUpload(Resource):

    @api_response
    @token_required("cloud_calculation")
    def post(self):
        from app.modules.order.order_services import add_item, Order, update_item
        from app.modules.importer.sources.bitrix24.order import run_export as run_order_export, find_association

        data = request.json
        user = get_logged_in_user()
        if user is None:
            raise ApiException("item_doesnt_exist", "Item doesn't exist.", 401)
        offer = get_offer_by_offer_number(data["offer_number"])
        if offer is None:
            raise ApiException("item_doesnt_exist", "Item doesn't exist.", 404)
        offer_v2_data = {"data": json.loads(json.dumps(offer.data))}
        offer_v2_data["data"]["offer_number"] = data["offer_number"]
        offer_v2_data["data"]["construction_date"] = data["construction_date"]
        offer_v2_data["data"]["smartme_number"] = data["smartme_number"]
        offer_v2_data["data"]["cloud_config_id"] = data["cloud_config_id"]
        offer_v2_data["data"]["signed_offer_pdf_id"] = data["signed_offer_pdf_id"]
        offer_v2_data["data"]["refund_transfer_pdf_id"] = data["refund_transfer_pdf_id"]
        offer_v2_data["data"]["old_power_invoice_id"] = data["old_power_invoice_id"]
        offer_v2_data["data"]["sepa_form_id"] = data["sepa_form_id"]
        offer_v2_data["data"]["bankowner"] = data["bankowner"]
        offer_v2_data["data"]["iban"] = data["iban"]
        offer_v2_data["data"]["bic"] = data["bic"]
        offer_v2_data["data"]["malo_lightcloud"] = data["malo_lightcloud"]
        offer_v2_data["data"]["malo_heatcloud"] = data["malo_heatcloud"]
        offer_v2_data["data"]["malo_ecloud"] = data["malo_ecloud"]
        offer_v2_data["data"]["malo_consumer1"] = data["malo_consumer1"]
        offer_v2_data["data"]["malo_consumer2"] = data["malo_consumer2"]
        offer_v2_data["data"]["malo_consumer3"] = data["malo_consumer3"]
        if "old_gas_invoice_id" in data:
            offer_v2_data["data"]["old_gas_invoice_id"] = data["old_gas_invoice_id"]
        offer_v2_data["is_sent"] = True
        offer = update_item_v2(id=offer.id, data=offer_v2_data)
        order = Order.query.filter(Order.offer_id == offer.id).first()
        order_data = {
            "datetime": datetime.datetime.now(),
            "lead_number": None,
            "label": offer.customer.lastname,
            "customer_id": offer.customer_id,
            "reseller_id": offer.reseller_id,
            "offer_id": offer.id,
            "category": "Cloud Verträge",
            "type": "",
            "street": offer.customer.default_address.street,
            "street_nb": offer.customer.default_address.street_nb,
            "zip": offer.customer.default_address.zip,
            "city": offer.customer.default_address.city,
            "data": offer.data,
            "value_net": offer.total,
            "contact_source": user["name"],
            "status": "new",
            "is_checked": False
        }
        if order is None:
            order = add_item(order_data)
            if order is None:
                raise ApiException("order-failed", "Order creation failed", 404)
        else:
            link = find_association("Order", local_id=order.id)
            if link is None:
                update_item(order.id, order_data)
            else:
                raise ApiException("already-sent", "Already sent", 412)
        run_order_export(local_id=order.id)
        return {"status": "success",
                "data": order.id}
