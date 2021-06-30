from operator import index
import base64
import re
import time
import json
import random
import pytz
from datetime import datetime, timedelta
import dateutil.parser

from app import db
from app.modules.user import auto_assign_lead_to_user
from app.modules.external.bitrix24.company import add_company
from app.modules.external.bitrix24.contact import get_contact_by_email, add_contact
from app.modules.external.bitrix24.deal import get_deals, add_deal
from app.modules.external.bitrix24.task import get_tasks, update_task, get_task
from app.modules.external.bitrix24.timeline_comment import add_timeline_comment
from app.modules.external.mfr.task import get_linked_data_by_task
from app.modules.settings import get_settings, set_settings
from app.utils.error_handler import error_handler
from app.utils.data_convert import street_to_street_with_nb, internationalize_phonenumber

from ._connector import get, post, put


def import_new_appointments():
    print("import etermin")
    config = get_settings(section="external/etermin")
    syncToken = 1
    if "SyncToken" in config:
        syncToken = config["SyncToken"]
    response = get("/api/appointmentsync", parameters={"synctoken": syncToken})
    if response is not None and "SyncToken" in response:
        for appointment in response["data"]:
            if appointment.get('SelectedAnswers') in [None, ""]:
                continue
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
                deal_data["service_appointment_startdate"] = pytz.timezone("Europe/Berlin").localize(startDatetime).isoformat()
                deal_data["service_appointment_enddate"] = pytz.timezone("Europe/Berlin").localize(endDatetime).isoformat()
                deal_data["etermin_id"] = f"{appointment['ID']}"
                deal_data["comments"] = f"Name: {appointment['FirstName']} {appointment['LastName']}<br>\nE-Mail: {appointment['Email']}<br>\n"
                deal_data["comments"] = f"{deal_data['comments']}Gebucht am: {appointment['BookingDate']}<br>\nOrt: {appointment['Location']}<br>\nThema: {appointment['SelectedAnswers']}<br>\nKommentar: {appointment['Notes']}"
                if appointment['SelectedAnswers'] == "PV Anlage ohne Speicher":
                    deal_data["mfr_category"] = "service"
                if appointment['SelectedAnswers'] == "PV Anlage mit Lithiumspeicher":
                    deal_data["mfr_category"] = "service_pv_storage_li"
                if appointment['SelectedAnswers'] == "PV Anlage mit Bleispeicher":
                    deal_data["mfr_category"] = "service_pv_storage_pb"
                if appointment['SelectedAnswers'] == "Lithiumspeicher ohne Photovoltaik-Anlage":
                    deal_data["mfr_category"] = "service_storage_li"
                if appointment['SelectedAnswers'] == "Bleispeicher ohne Photovoltaik-Anlage":
                    deal_data["mfr_category"] = "service_storage_pb"
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
        "select[0]": "TITLE",
        "select[1]": "DESCRIPTION",
        "select[2]": "UF_CRM_TASK",
        "select[3]": "CONTACT_ID",
        "select[4]": "COMPANY_ID",
        "select[5]": "TIME_ESTIMATE",
        "select[6]": "UF_AUTO_422491195439",
        "select[7]": "STATUS",
        "select[8]": "START_DATE_PLAN",
        "select[9]": "END_DATE_PLAN",
        "select[10]": "RESPONSIBLE_ID",
        "select[11]": "ACCOMPLICES",
        "select[12]": "SUBORDINATE",
        "select[13]": "AUDITORS",
        "select[14]": "DEADLINE",
        "select[15]": "UF_AUTO_219922666303",
        "select[16]": "UF_AUTO_343721853755",
        "select[17]": "UF_AUTO_513701476131",
        "filter[>CHANGED_DATE]": last_task_export_time,
        "filter[TITLE]": "%[mfr]%"
    })
    last_task_export_time = datetime.now()
    if tasks is None:
        return
    for task in tasks:
        export_appointment(task)
    config = get_settings("external/etermin")
    if config is not None:
        config["last_task_export_time"] = last_task_export_time.astimezone().isoformat()
    set_settings("external/etermin", config)


def export_appointment(task):
    print("export task ", task.get("id"))
    if task.get("startDatePlan") in [None, "", "0"]:
        print("no start date")
        return
    if task.get("mfr_appointments") in [0, "", None]:
        print("no mfr_appointments")
        return
    if task.get("mfr_appointments")[:1] in ["{", "["]:
        appointments = json.loads(task.get("mfr_appointments"))
    else:
        appointments = json.loads(base64.b64decode(task.get("mfr_appointments").encode('utf-8')).decode('utf-8'))
    if task.get("etermin_appointments") not in [0, "", None]:
        if task.get("etermin_appointments")[:1] in ["{", "["]:
            old_etermin_appointments = json.loads(task.get("etermin_appointments"))
        else:
            old_etermin_appointments = json.loads(base64.b64decode(task.get("etermin_appointments").encode('utf-8')).decode('utf-8'))
    else:
        old_etermin_appointments = []
    etermin_appointments = []
    i = 0
    for appointment in appointments:
        etermin_appointment = {
            "start": appointment.get("StartDateTime"),
            "end": appointment.get("EndDateTime"),
            "bitrix_user_ids": appointment.get("bitrix_user_ids")
        }
        if i < len(old_etermin_appointments):
            if "etermin_id" in old_etermin_appointments[i]:
                etermin_appointment["etermin_id"] = old_etermin_appointments[i]["etermin_id"]
        if i == 0:
            etermin_appointment["etermin_id"] = task.get("etermin_id")
        etermin_appointments.append(etermin_appointment)
        i = i + 1
    i = 0
    if json.dumps(old_etermin_appointments) != json.dumps(etermin_appointments) and len(etermin_appointments) > 0:
        for etermin_appointment in etermin_appointments:
            start_datetime = dateutil.parser.parse(etermin_appointment["start"]).strftime("%Y-%m-%d %H:%M:%S")
            end_datetime = dateutil.parser.parse(etermin_appointment["end"]).strftime("%Y-%m-%d %H:%M:%S")
            if etermin_appointment.get("etermin_id") not in [None, "", "0"]:
                post_data = {
                    "id": etermin_appointment.get("etermin_id"),
                    "start": start_datetime,
                    "end": end_datetime
                }
                print("export task update etermin", task["id"])
                response = put("/api/appointment", post_data=post_data)
                if response.get("status", "") != "success":
                    print("etermin-error:", response)
            else:
                if "90" not in etermin_appointment.get("bitrix_user_ids"):
                    continue
                deal_data, contact_data, company_data = get_linked_data_by_task(task)
                if deal_data is not None and deal_data.get("etermin_id") not in [None, "", "0"]:
                    continue
                if deal_data is None and contact_data is None:
                    continue
                post_data = {
                    "start": start_datetime,
                    "end": end_datetime,
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
                post_data["location"] = f'{post_data["street"]}, {post_data["zip"]} {post_data["city"]}'
                print("export task etermin", task["id"])
                response = post("/api/appointment", post_data=post_data)
                if response is not None and "cid" in response:
                    etermin_appointment["etermin_id"] = response["cid"]
                else:
                    print("post_data:", post_data)
                    print("etermin-error:", response)
        update_task(task["id"], {
            "etermin_id": etermin_appointments[0]["etermin_id"],
            "etermin_appointments": base64.b64encode(json.dumps(etermin_appointments).encode('utf-8')).decode('utf-8')
        })
