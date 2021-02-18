from app.modules.external.bitrix24.company import get_company
from app.modules.external.bitrix24.contact import get_contact
from app.modules.external.bitrix24.deal import get_deal
import time
import json
import random
from datetime import datetime, timedelta

from app import db
from app.modules.external.bitrix24.task import get_task, update_task, get_tasks
from app.modules.settings import get_settings, set_settings

from ._connector import get, post, put
from .contact import export_by_bitrix_id as export_contact_by_bitrix_id
from .company import export_by_bitrix_id as export_company_by_bitrix_id


def get_export_data(task_data, contact_data, deal_data, company_data):
    main_mfr_id = 0
    service_objects = []
    if contact_data is not None and contact_data.get("mfr_service_object_id") not in [None, "", "0", 0]:
        main_mfr_id = contact_data.get("mfr_id")
        service_objects.append({"Id": contact_data.get("mfr_service_object_id")})
    if company_data is not None and company_data.get("mfr_service_object_id") not in [None, "", "0", 0]:
        main_mfr_id = company_data.get("mfr_id")
        service_objects.append({"Id": company_data.get("mfr_service_object_id")})

    data = {
        "CreateFromServiceRequestTemplateId": get_template_id_by_deal(deal_data),
        "Name": f"{contact_data.get('first_name')} {contact_data.get('last_name')}",
        "ServiceObjects": service_objects,
        "CustomerId": main_mfr_id,
        "Description": task_data.get("description", "").replace("\n", "<br>\n"),
        "ExternalId": task_data.get("id"),
        "State": "ReadyForScheduling"
    }
    if task_data.get("timeestimate") not in [None, "", "0", 0]:
        data["TargetTimeInMinutes"] = str(int(int(task_data.get("timeestimate")) / 60))
    return data


def get_import_data(raw):
    data = {}
    return data


def run_cron_export():

    config = get_settings("external/mfr")
    print("export task mfr")
    if config is None:
        print("no config for export task mfr")
        return None
    last_task_export_time = config.get("last_task_export_time", "2021-01-01")
    tasks = get_tasks({
        "select[0]": "ID",
        "filter[>CHANGED_DATE]": last_task_export_time,
        "filter[TITLE]": "%[mfr]%"
    })
    print(tasks)
    last_task_export_time = datetime.now()
    for task in tasks:
        export_by_bitrix_id(task["id"])
    config = get_settings("external/mfr")
    if config is not None:
        config["last_task_export_time"] = str(last_task_export_time)
    set_settings("external/mfr", config)


def export_by_bitrix_id(bitrix_id):
    task_data = get_task(bitrix_id)
    deal_data, contact_data, company_data = get_linked_data_by_task(task_data)
    if contact_data is not None:
        export_contact_by_bitrix_id(contact_data["id"])
        contact_data = get_contact(contact_data["id"])
    else:
        if company_data is not None:
            export_company_by_bitrix_id(company_data["id"])
            company_data = get_company(company_data["id"])
    post_data = get_export_data(task_data, contact_data, deal_data, company_data)
    if task_data.get("mfr_id", None) in ["", None, 0]:
        response = post("/ServiceRequests", post_data=post_data)
        if response.get("Id") not in ["", None, 0]:
            update_task(bitrix_id, {"mfr_id": response.get("Id")})
        else:
            print(json.dumps(response, indent=2))
    else:
        response = put(f"/ServiceRequests({task_data.get('mfr_id')}L)", post_data=post_data)


def get_linked_data_by_task(task_data):
    if not isinstance(task_data.get("ufCrmTask"), list):
        return None, None, None
    contact_id = None
    company_id = None
    deal_id = None
    contact_data = None
    company_data = None
    deal_data = None
    for crm_element in task_data.get("ufCrmTask"):
        if crm_element[:2] == "C_":
            contact_id = crm_element[2:]
        if crm_element[:3] == "CO_":
            company_id = crm_element[2:]
        if crm_element[:2] == "D_":
            deal_id = crm_element[2:]
    if deal_id is not None:
        deal_data = get_deal(deal_id)
        if contact_id is None and company_id is None:
            if deal_data["contact_id"] not in [None, "", "0", 0]:
                contact_id = deal_data["contact_id"]
            else:
                if deal_data["company_id"] not in [None, "", "0", 0]:
                    company_id = deal_data["company_id"]
    if contact_id is not None:
        contact_data = get_contact(contact_id)
        if contact_data["company_id"] not in [None, "", "0", 0]:
            company_data = get_company(contact_data["company_id"])
    else:
        if company_id is not None:
            company_data = get_company(company_id)
    return deal_data, contact_data, company_data


def get_template_id_by_deal(deal_data):
    config = {
        "default": "17991565319",
        "electric": "17432084483",
        "service": "17991565318",
        "roof": "17991565317",
        "heating": "17996480515",
        "holiday": "17996480515",
        "roof_reconstruction_pv": "18134892576"
        "roof_reconstruction": "18145247234",
        "service_storage_pb": "18134892577",
        "service_storage_li": "18134892579",
        "service_pv_storage_li": "18147409921",
        "service_pv_storage_pb": "18147409922",
        "storage_swap": "18145247235",
        "repair_electric": "18137612317",
        "additional_roof": "18145247236",
        "solar_edge_change_test": "18147409920"
    }
    if deal_data is None:
        return config["default"]
    if deal_data.get("mfr_category", "") in config:
        return config[deal_data.get("mfr_category", "")]
    if deal_data.get("category_id", "") == "32":
        return config["electric"]
    if deal_data.get("category_id", "") == "1":
        return config["roof"]
    if deal_data.get("category_id", "") == "9":
        return config["heating"]
    if deal_data.get("category_id", "") == "134":
        return config["service"]
    return config["default"]
