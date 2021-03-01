import re
import time
import json
import random
from datetime import datetime, timedelta
import dateutil.parser

from app import db
from app.modules.user import auto_assign_lead_to_user
from app.modules.external.bitrix24.company import add_company
from app.modules.external.bitrix24.contact import get_contact_by_email, add_contact
from app.modules.external.bitrix24.deal import get_deals, add_deal
from app.modules.external.bitrix24.task import get_tasks
from app.modules.external.bitrix24.timeline_comment import add_timeline_comment
from app.modules.external.mfr.task import get_linked_data_by_task
from app.modules.settings import get_settings, set_settings
from app.utils.error_handler import error_handler
from app.utils.data_convert import street_to_street_with_nb, internationalize_phonenumber

from ._connector import get, post


def import_new_appointments():
    print("import etermin")
    config = get_settings(section="external/etermin")
    syncToken = 1
    if "SyncToken" in config:
        syncToken = config["SyncToken"]
    response = get("/api/appointmentsync", parameters={"synctoken": syncToken})
    if response is not None and "SyncToken" in response:
        for appointment in response["data"]:
            existing_deals = get_deals({"FILTER[UF_CRM_1614177772351]": appointment['ID']})
            if len(existing_deals) == 0:
                contact = get_contact_by_email(appointment["Email"])
                deal_data = {
                    "stage_id": "C134:NEW",
                    "category_id": "134"
                }
                startDatetime = dateutil.parser.parse(appointment['StartDateTime'])
                endDatetime = dateutil.parser.parse(appointment['EndDateTime'])
                if contact is None:
                    deal_data["firstname"] = appointment["FirstName"]
                    deal_data["lastname"] = appointment["LastName"]
                    deal_data["street"] = appointment["Street"]
                    deal_data["zip"] = appointment["ZIP"]
                    deal_data["city"] = appointment["Town"]
                    deal_data["email"] = appointment["Email"]
                    deal_data["phone"] = appointment["Phone"]
                    deal_data["title"] = f"{appointment['LastName']} {appointment['FirstName']} {appointment['Town']} am {startDatetime.strftime('%d.%m.%Y')}"
                else:
                    deal_data["contact_id"] = contact["id"]
                    deal_data["title"] = f"{contact['last_name']} {contact['first_name']} {contact['city']} am {startDatetime.strftime('%d.%m.%Y')}"
                deal_data["service_appointment_notes"] = f"Wartungstermin für den {startDatetime.strftime('%d.%m.%Y %H:%M:%S')} bis {endDatetime.strftime('%d.%m.%Y %H:%M:%S')} // eTermin"
                deal_data["service_appointment_date"] = startDatetime.strftime('%d.%m.%Y')
                deal_data["etermin_id"] = f"{appointment['ID']}"
                deal_data["comments"] = f"Gebucht am: {appointment['BookingDate']}<br>\nThema: {appointment['SelectedAnswers']}"
                print("add deal", add_deal(deal_data))
        config = get_settings("external/etermin")
        if config is not None:
            config["SyncToken"] = response["SyncToken"]
        set_settings("external/etermin", config)


def export_appointments():
    config = get_settings("external/etermin")
    print("export task etermin")
    if config is None:
        print("no config for export task etermin")
        return None
    last_task_export_time = config.get("last_task_export_time", "2021-01-01")
    tasks = get_tasks({
        "select[0]": "ID",
        "select[1]": "TITLE",
        "select[2]": "CONTACT_ID",
        "select[3]": "COMPANY_ID",
        "select[4]": "UF_AUTO_422491195439",
        "select[5]": "UF_AUTO_219922666303",
        "select[6]": "STATUS",
        "select[7]": "START_DATE_PLAN",
        "select[8]": "END_DATE_PLAN",
        "select[9]": "UF_CRM_TASK",
        "filter[RESPONSIBLE_ID]": 90,
        "filter[>CHANGED_DATE]": last_task_export_time,
        "filter[TITLE]": "%[mfr]%"
    })
    last_task_export_time = datetime.now()
    for task in tasks:
        if task.get("startDatePlan") in [None, "", "0"]:
            continue
        deal_data, contact_data, company_data = get_linked_data_by_task(task)
        startDatetime = dateutil.parser.parse(task.get("startDatePlan"))
        endDatetime = dateutil.parser.parse(task.get("endDatePlan"))
        post_data = {
            "start": startDatetime.strftime("%Y-%m-%d %H:%M:%S"),
            "end": endDatetime.strftime("%Y-%m-%d %H:%M:%S"),
            "calendarid": 93100,
            "sendemail": False
        }
        if company_data is not None:
            post_data["street"] = company_data["street"]
            post_data["zip"] = company_data["zip"]
            post_data["city"] = company_data["city"]
        if contact_data is not None:
            post_data["firstname"] = contact_data["first_name"]
            post_data["lastname"] = contact_data["last_name"]
            post_data["street"] = contact_data["street"]
            post_data["zip"] = contact_data["zip"]
            post_data["city"] = contact_data["city"]
        print(post_data)
        response = post("/api/appointment", post_data=post_data)
        print(response)
        return
    config = get_settings("external/etermin")
    if config is not None:
        config["last_task_export_time"] = str(last_task_export_time)
    set_settings("external/etermin", config)
