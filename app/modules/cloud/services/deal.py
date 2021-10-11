from datetime import datetime
import json
from app import db

from app.modules.external.bitrix24.deal import get_deal, get_deals, add_deal, update_deal
from app.modules.external.bitrix24.drive import get_folder, get_folder_id
from app.modules.external.fakturia.deal import store_json_data, load_json_data, normalize_contract_number
from app.modules.offer.models.offer_v2 import OfferV2


def cron_split_cloud_contract():
    print("split_cloud_contract")
    deals = get_deals({
        "SELECT": "full",
        "FILTER[CATEGORY_ID]": "15",
        "FILTER[STAGE_ID]": "C15:17",
    })
    for deal in deals:
        print(deal.get("id"), deal.get("is_cloud_master_deal"))
        if deal.get("is_cloud_master_deal") not in [1, "1", True, "true"]:
            continue
        fakturia_data = load_json_data(deal.get("fakturia_data"))
        if fakturia_data is None or "item_lists" not in fakturia_data:
            continue
        offer = OfferV2.query.options(db.subqueryload("items")).filter(OfferV2.number == deal.get("cloud_number")).first()
        if offer is None:
            continue
        print(deal.get("id"))
        consumer_index = 0
        last_list = fakturia_data["item_lists"][len(fakturia_data["item_lists"]) - 1]
        add_deals = []
        for item in last_list["items"]:
            copy_deal = json.loads(json.dumps(deal))
            del copy_deal["fakturia_data"]
            del copy_deal["is_cloud_master_deal"]
            copy_deal["stage_id"] = "C15:21"
            if item.get("type") == "heatcloud":
                copy_deal["title"] = normalize_contract_number(deal.get("cloud_contract_number")) + "w1 | " + copy_deal["title"]
                copy_deal["is_cloud_heatcloud"] = "1"
                copy_deal["cloud_type"] = ["Wärmecloud"]
                copy_deal["counter_main"] = offer.data["heatcloud_power_meter_number"]
                add_deals.append(copy_deal)
            if item.get("type") == "consumer":
                copy_deal["is_cloud_consumer"] = "1"
                copy_deal["cloud_type"] = ["Consumer"]
                copy_deal["title"] = normalize_contract_number(deal.get("cloud_contract_number")) + f"c{consumer_index + 1} | " + copy_deal["title"]
                copy_deal["counter_main"] = offer.data["consumers"][consumer_index].get("power_meter_number")
                copy_deal["malo_id"] = offer.data["consumers"][consumer_index].get("malo_id")
                copy_deal["cloud_street"] = offer.data["consumers"][consumer_index].get("address").get("street")
                copy_deal["cloud_street_nb"] = offer.data["consumers"][consumer_index].get("address").get("street_nb")
                copy_deal["cloud_city"] = offer.data["consumers"][consumer_index].get("address").get("city")
                copy_deal["cloud_zip"] = offer.data["consumers"][consumer_index].get("address").get("zip")
                add_deals.append(copy_deal)
                consumer_index = consumer_index + 1
            if item.get("type") == "ecloud":
                copy_deal["is_cloud_ecloud"] = "1"
                copy_deal["cloud_type"] = ["eCloud"]
                copy_deal["title"] = normalize_contract_number(deal.get("cloud_contract_number")) + f"ecG | " + copy_deal["title"]
                add_deals.append(copy_deal)
        for copy_deal_data in add_deals:
            add_deal(copy_deal_data)
        update_deal(deal.get("id"), { "stage_id": "C15:21" })


def cron_mein_portal_initial_documents():
    print("mein_portal_initial_documents")
    return
    deals = get_deals({
        "SELECT": "full",
        "FILTER[CATEGORY_ID]": "172",
        "FILTER[STAGE_ID]": "C172:NEW"
    })
    for deal in deals:
        print(deal["id"])
        folder_id = get_folder_id(649168, path=f"Kunde {deal['contact_id']}/Datenblätter")
        if folder_id is None:
            continue
        auto_documents = get_folder(folder_id, "01 Dokumappe.pdf")
        if len(auto_documents) > 0:
            print("move")
            # update_deal(deal["id"], {"STAGE_ID": "C172:1"})
        else:
            print("generate")

    '''
    deals = get_deals({
        "SELECT": "full",
        "FILTER[CATEGORY_ID]": "32",
        "FILTER[STAGE_ID]": "C32:WON",
        "FILTER[>DATE_MODIFY]": "2021-07-01"
    })
    deals2 = get_deals({
        "SELECT": "full",
        "FILTER[CATEGORY_ID]": "32",
        "FILTER[STAGE_ID]": "C32:21",
        "FILTER[>DATE_MODIFY]": "2021-07-01"
    })
    if deals is None:
        deals = deals2
    else:
        if deals is not None:
            deals = deals + deals2
    for deal in deals:
        if deal.get("auto_document_check") not in [None, "None", ""]:
            continue
        print(deal["id"])
        print(deal.get("auto_document_check"))
        folder_id = get_folder_id(649168, path=f"Kunde {deal['contact_id']}/Datenblätter")
        if folder_id is not None:
            auto_documents = get_folder(folder_id, "01 Dokumappe.pdf")
            if len(auto_documents) > 0:
                print(auto_documents)
                print(deal["id"])
                update_deal(deal["id"], {"auto_document_check": datetime.now()})'''