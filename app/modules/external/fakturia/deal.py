import re
import json
import base64

from app import db
from app.models import OfferV2
from app.modules.external.bitrix24.deal import get_deal, get_deals
from app.modules.settings import get_settings


def get_contract_data_by_deal(deal_id):
    config = get_settings("external/bitrix24")
    deal = get_deal(deal_id)
    if deal is not None:
        if deal.get("category_id") != "15":
            return {"status": "failed", "data": {"error": "Nur in Cloud Pipeline verfügbar"}, "message": ""}
        offer = OfferV2.query.options(db.subqueryload("items")).filter(OfferV2.number == deal.get("cloud_number")).first()
        if offer is None:
            return {"status": "failed", "data": {"error": "Cloud Angebot nicht gefunden"}, "message": ""}
        data = {
            "id": deal.get("id"),
            "cloud_number": deal.get("cloud_number"),
            "cloud_contract_number": normalize_contract_number(deal.get("cloud_contract_number")),
            "items": []
        }
        payload = {"SELECT[0]": "*"}
        for field in config["deal"]["fields"].values():
            payload[f"SELECT[{len(payload)}]"] = field
        payload["FILTER[UF_CRM_1596704551167]"] = f'{data.get("cloud_contract_number")}'
        data["deals"] = get_deals(payload)

        for item in data["deals"]:
            item["link"] = f"https://keso.bitrix24.de/crm/deal/details/{item['id']}/"
            if len(item["cloud_type"]) > 0:
                if item["cloud_type"][0] == "Zero":
                    item["type"] = "lightcloud"
                    item["cloud_type"] = "cCloud-Zero"
                    data["main_deal"] = item
                if item["cloud_type"][0] == "Wärmecloud":
                    item["type"] = "heatcloud"
                    item["cloud_type"] = "Wärmecloud"
                if item["cloud_type"][0] == "eCloud":
                    item["type"] = "ecloud"
                    item["cloud_type"] = "eCloud"
                if item["cloud_type"][0] == "Consumer":
                    item["type"] = "consumer"
                    item["cloud_type"] = "Consumer"
        data["fakturia"] = load_json_data(data["main_deal"]["fakturia_data"])

        for item in offer.items:
            item_data = {
                "type": "text",
                "label": item.label,
                "description": item.description,
                "tax_rate": int(item.tax_rate),
                "total_price": float(item.total_price),
                "total_price_net": float(item.total_price_net),
                "deal": None
            }
            data["items"].append(item_data)
        return data
    return None


def load_json_data(field_data):
    if field_data is None:
        return None
    return json.loads(base64.b64decode(field_data.encode('utf-8')).decode('utf-8'))


def store_json_data(data):
    return base64.b64encode(json.dumps(data).encode('utf-8')).decode('utf-8')


def normalize_contract_number(cloud_contract_number):
    number = re.findall(r'C[0-9]+', cloud_contract_number)
    if len(number) > 0:
        return number[0]
    return cloud_contract_number
