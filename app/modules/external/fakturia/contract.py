import json
from datetime import datetime
from operator import pos

from app import db
from app.modules.settings import set_settings, get_settings
from app.modules.external.bitrix24.contact import get_contact, get_contacts_by_changedate as get_bitrix_contacts_by_changedate
from app.modules.external.bitrix24.deal import get_deal
from app.modules.external.bitrix24.company import get_company as get_bitrix_company
from app.utils.error_handler import error_handler

from ._connector import get, post, put


def get_export_data(deal, contact):
    delivery_begin = deal.get("cloud_delivery_begin")[0:deal.get("cloud_delivery_begin").find("T")]
    data = {
        "customerNumber": contact.get("fakturia_number"),
        "projectName": "Cloud Verträge",
        "subscription": {
            "termPeriod": 1,
            "termUnit": "MONTH",
            "noticePeriod": 0,
            "noticeUnit": "DAY",
            "continuePeriod": 0,
            "continueUnit": "DAY",
            "billedInAdvance": True,
            "subscriptionItems": [
            {
                "itemNumber": "BSH Cloud",
                "quantity": 1,
                "extraDescription": "",
                "name": "BSH Cloud",
                "description": "",
                "unit": "PIECE",
                "validFrom": delivery_begin,
                "ccQuantityChange": False,
                "status": "ACTIVE",
                "activityType": "DEFAULT_PERFORMANCE"
            }
            ],
            "status": "DRAFT"
        },
        "contractNumber": int(deal.get("contract_number").replace("C", "")),
        "name": deal.get("contract_number"),
        "issueDate": delivery_begin,
        "recur": 1,
        "recurUnit": "MONTH",
        "duePeriod": 0,
        "dueUnit": "DAY",
        "paymentMethod": "BANKTRANSFER",
        "contractStatus": "DRAFT",
        "trialPeriod": 0,
        "trialUnit": "DAY",
        "trialPeriodEndAction": "CONTINUE",
        "hasTrialperiod": False,
        "ccDisallowTermination": True,
        "taxConfig": "AUTOMATIC",
        "documentDeliveryMode": "EMAIL"
    }
    return data


def export_cloud_deal(deal_id):
    print("export deal:", deal_id)
    deal = get_deal(deal_id)
    contact = get_contact(deal.get("contact_id"))
    if contact.get("fakturia_number") not in ["", None]:
        export_data = get_export_data(deal, contact)
        if export_data is not None:
            if deal.get("fakturia_contract_number") in ["", None, 0, "0"]:
                contract_data = post(f"/Contracts", post_data=export_data)
                if contract_data is not None and "contractNumber" in contract_data:
                    print(json.dumps(contract_data, indent=2))
                else:
                    print(json.dumps(contract_data, indent=2))
            else:

                contract_data = put(f"/Contracts/{deal.get('fakturia_contract_number')}", post_data=export_data)
                print(json.dumps(contract_data, indent=2))
                if contract_data is not None and "contractNumber" in contract_data:
                    for item in contract_data.get("subscription").get("subscriptionItems"):
                        post(f"/Contracts/{deal.get('fakturia_contract_number')}/Subscription/SubscriptionItems/{item.get('uuid')}/customPrices", post_data={
                            "cost": 15.42,
                            "currency": "EUR",
                            "validFrom": "",
                            "minimumQuantity": 1
                        })
    else:
        print(contact["id"], "no customer number")
