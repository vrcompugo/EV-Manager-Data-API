import json
import datetime
import base64
from werkzeug import FileStorage

from app.exceptions import ApiException
from app.modules.external.bitrix24.deal import get_deal, update_deal
from app.modules.external.bitrix24.contact import get_contact
from app.modules.external.bitrix24.drive import get_folder_id, get_folder, get_file_content
from app.modules.cloud.services.contract import get_contract_data, normalize_date
from app.modules.settings import get_settings

from ._connector import post
from .models.enbw_contract import ENBWContract


def get_tarifs(contract: ENBWContract):
    deal = get_deal(contract.deal_id, force_reload=True)
    requested_usage = int(deal.get("delivery_usage")) * 0.5
    address_data = {
        "area_code": "05631",
        "city": deal.get("delivery_city"),
        "email": "",
        # "phone_number": contact.get("phone")[0].get("VALUE"),
        "phone_number": "501717",
        "street_name": deal.get("delivery_street"),
        "street_number": deal.get("delivery_street_nb"),
        "zipcode": deal.get("delivery_zip")
    }
    tarif_type = 1
    if deal.get("is_cloud_heatcloud") in ["1", "Y", True, "true"]:
        tarif_type = 2
    tarif_request = {
        "tariff_type": tarif_type, # 1 = Strom, 2 = Heating
        "customer_type": 0,
        "client_type": 0,
        "counter_type": 0,
        "query_date": normalize_date(datetime.datetime.now()).strftime("%d.%m.%Y"),
        "brand": "0",
        "tariff_variant": 0,
        "consumption": requested_usage,
        "zip": address_data["zipcode"],
        "city": address_data["city"],
        "street": f'{address_data["street_name"]} {address_data["street_number"]}'
    }
    tarif_data = post("/tariffs", tarif_request, contract=contract)
    if "data" not in tarif_data or "tariffs" not in tarif_data["data"] or len(tarif_data["data"]["tariffs"]) == 0:
        raise ApiException("no valid tarif", "Kein ENBW Tariff für die Kundendaten gefunden")
    for tarif in tarif_data["data"]["tariffs"]:
        tarif["label"] = tarif.get("tariff_name") + " " + tarif.get("base_tariff").get("tariff_id") + " " + tarif.get("base_price_monthly_de") + " " + tarif.get("kwh_price_cent_raw_de") + " " + tarif.get("yearly_price_de")
    return tarif_data["data"]["tariffs"]