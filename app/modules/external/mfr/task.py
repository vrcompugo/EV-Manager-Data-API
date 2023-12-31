import base64
from io import BytesIO

from flask_cors.core import try_match
from app.modules.external.bitrix24.company import get_company
from app.modules.external.bitrix24.contact import get_contact
from app.modules.external.bitrix24.deal import get_deal
from app.modules.external.bitrix24.user import get_user_by_email, get_user
import time
import magic
import json
import random
import pytz
import tempfile
from datetime import datetime, timedelta
import dateutil.parser

from app import db
from app.modules.external.bitrix24.task import get_task, update_task, get_tasks
from app.modules.external.bitrix24.drive import add_file, create_folder_path, get_file_content, get_folder_id, get_folder
from app.modules.settings import get_settings, set_settings
from app.modules.external.bitrix24._connector import post as post_bitrix
from app.models import QuoteHistory

from ._connector import get, post, put, get_download
from .contact import export_by_bitrix_id as export_contact_by_bitrix_id
from .company import export_by_bitrix_id as export_company_by_bitrix_id
from .models.task_persistent_users import TaskPersistentUsers
from .models.mfr_import_buffer import MfrImportBuffer
from .models.mfr_export_buffer import MfrExportBuffer


def get_export_data(task_data, contact_data, deal_data, company_data):
    main_mfr_id = 0
    service_objects = []
    if contact_data is not None and contact_data.get("mfr_service_object_id") not in [None, "", "0", 0]:
        main_mfr_id = contact_data.get("mfr_id")
        service_objects.append({"Id": contact_data.get("mfr_service_object_id")})
    if company_data is not None and company_data.get("mfr_service_object_id") not in [None, "", "0", 0]:
        main_mfr_id = company_data.get("mfr_id")
        service_objects.append({"Id": company_data.get("mfr_service_object_id")})
    task_link = f'<a href="https://keso.bitrix24.de/company/personal/user/15/tasks/task/view/{task_data["id"]}/" target="_blank">Bitrix-Aufgabenlink</a>'
    task_data["comment_files"] = []
    comment_list = ""
    if task_data.get("comments") is not None:
        for comment in task_data.get("comments"):
            if comment['POST_MESSAGE'].find("Verantwortliche Person bestimmt:") >= 0:
                continue
            if comment['POST_MESSAGE'].find("Mitwirkende zugefügt:") >= 0:
                continue
            if comment['POST_MESSAGE'].find("Sie sollten die Aufgabe schließen oder heute noch die Frist ändern.") >= 0:
                continue
            if comment['POST_MESSAGE'].find("Aufgabe geschlossen.") >= 0:
                continue
            if comment['POST_MESSAGE'].find("Frist geändert:") >= 0:
                continue
            if comment['POST_MESSAGE'].find("Sie sollten die Aufgabe schließen oder die Frist ändern.") >= 0:
                continue
            if comment['POST_MESSAGE'].find("Beobachter zugefügt:") >= 0:
                continue
            post_date = dateutil.parser.parse(comment['POST_DATE'])
            comment_list = comment_list + f"{post_date.strftime('%d.%m.%Y %H:%M:%S')} von {comment['AUTHOR_NAME']}<br>\n{comment['POST_MESSAGE']}<br>\n{'-' * 20}<br>\n"
            if comment.get("ATTACHED_OBJECTS") not in [None, "", 0]:
                for key in comment.get("ATTACHED_OBJECTS").keys():
                    task_data["comment_files"].append(comment.get("ATTACHED_OBJECTS")[key])
    data = {
        "CreateFromServiceRequestTemplateId": get_template_id_by_deal(deal_data),
        "Name": f"{contact_data.get('first_name')} {contact_data.get('last_name')}",
        "ServiceObjects": service_objects,
        "CustomerId": main_mfr_id,
        "Description": f'{task_link}<br>\n<br>\nKommentare:<br>\n{comment_list}<br><br>\n' + task_data.get("description", "").replace("\n", "<br>\n"),
        "ExternalId": task_data.get("id"),
        "State": "ReadyForScheduling"
    }
    if task_data.get("timeestimate") not in [None, "", "0", 0]:
        data["TargetTimeInMinutes"] = str(int(int(task_data.get("timeestimate")) / 60))
    if deal_data is not None:
        folder_id = None
        if str(deal_data.get("category_id")) in ["1", "44"]:
            traufhohe = 0
            roof_toppings = ""
            if deal_data.get("unique_identifier") not in [None, ""]:
                quote_history = QuoteHistory.query.filter(QuoteHistory.lead_id == deal_data.get("unique_identifier")).order_by(QuoteHistory.datetime.desc()).first()
                if quote_history is not None and "data" in quote_history.data and "roofs" in quote_history.data["data"]:
                    for roof in quote_history.data["data"]["roofs"]:
                        if float(roof.get("traufhohe", 0)) > traufhohe:
                            traufhohe = float(roof.get("traufhohe", 0))
                        if roof.get('roof_topping') not in [None, ""]:
                            roof_toppings = roof_toppings + f"{roof.get('roof_topping')}, "
                if roof_toppings == "":
                    roof_toppings = "?"
                if traufhohe == 0:
                    traufhohe = "?"
                planned_teamlead = "?"
                if deal_data["planned_teamlead"] is not None and len(deal_data["planned_teamlead"]) > 0 and deal_data["planned_teamlead"][0] not in ["106", 106]:
                    planned_teamlead = get_user(deal_data["planned_teamlead"][0])["LAST_NAME"]
                data["Name"] =  data["Name"] + f", {traufhohe} Meter, Team {planned_teamlead}, {roof_toppings}, KW {deal_data.get('construction_calendar_week')}"
            files = []
            print(deal_data.get("upload_link_tab"))
            if deal_data.get("upload_link_tab") not in [None, ""]:
                folder_id = get_folder_id(parent_folder_id=442678, path=deal_data.get("upload_link_tab").replace("https://keso.bitrix24.de/docs/path/Auftragsordner/", ""))
                print(deal_data.get("upload_link_tab"), folder_id)
        if str(deal_data.get("category_id")) == "32":
            folder_id = get_folder_id(parent_folder_id=442678, path=deal_data.get("upload_link_electric").replace("https://keso.bitrix24.de/docs/path/Auftragsordner/", ""))
        if str(deal_data.get("category_id")) == "9":
            folder_id = get_folder_id(parent_folder_id=442678, path=deal_data.get("upload_link_heating").replace("https://keso.bitrix24.de/docs/path/Auftragsordner/", ""))
        if folder_id is not None:
            files = get_folder(folder_id)
            data["documents"] = files
    return data


def convert_datetime(value, zone="Europe/Berlin"):
    if value is None:
        return None
    return dateutil.parser.parse(value).astimezone(pytz.timezone(zone)).strftime("%Y-%m-%dT%H:%M:00")


def import_by_id(service_request_id):
    print("mfr import", service_request_id)
    config_folders = get_settings("external/bitrix24/folder_creation")
    drive_abnahmen_folder = next((item for item in config_folders["folders"] if item["key"] == "drive_abnahmen_folder"), None)
    response = get(f"/ServiceRequests({service_request_id}L)?$expand=ServiceObjects,Customer,Reports,Items,Appointments/Contacts,Steps,Comments,StockMovements", parameters={
        "id": service_request_id
    })
    if response.get("ExternalId", None) is None:
        return
    buffer_data = MfrImportBuffer.query.filter(MfrImportBuffer.service_request_id == service_request_id).first()
    if buffer_data is None:
        buffer_data = MfrImportBuffer(service_request_id=service_request_id, data=response)
        db.session.add(buffer_data)
        db.session.commit()
    else:
        changes_found = False
        important_fields = ["State", "Reports", "Appointments"]
        for field in important_fields:
            if json.dumps(buffer_data.data.get(field)) != json.dumps(response.get(field)):
                changes_found = True
                break
        if changes_found is False:
            print("no import needed")
            return
    buffer_data.last_change = datetime.now()
    db.session.commit()

    task_id = response["ExternalId"]
    if task_id.find("-") > 0:
        task_id = task_id[0:task_id.find("-")]
    task_data = get_task(task_id)
    if task_data is None:
        return
    persistent_users = TaskPersistentUsers.query.filter(TaskPersistentUsers.bitrix_task_id == task_id).first()
    if persistent_users is None:
        persistent_users = TaskPersistentUsers(
            bitrix_task_id=task_id,
            data=task_data["accomplices"]
        )
        db.session.add(persistent_users)
        db.session.commit()
    update_data = {}
    if response["State"] in ["IsWorkDone", "Closed"] and task_data["status"] not in ["4", "5"]:
        update_data["status"] = "4"
        if len(response.get("Reports", [])) == 0:
            deal_data, contact_data, company_data = get_linked_data_by_task(task_data)
            if contact_data is not None and contact_data.get("id") not in [None, "", "0"]:
                report = post(f"/ServiceRequests({service_request_id}L)/GenerateReportHash", post_data={
                    "reportDefinitionId": "18146623488"
                })
                if "value" in report:
                    report_content = get_download(f"/System/CustomerReport/{report['value']}")
                    folder_id = create_folder_path(drive_abnahmen_folder["folder_id"], f"Kunde {contact_data['id']}")
                    add_file(folder_id, {
                        "filename": f"Abnahme MFR ({task_data['id']}).pdf",
                        "file_content": report_content.content
                    })
    if len(response.get("Appointments", [])) > 0:
        appointment = response["Appointments"][0]
        last_appointment = response["Appointments"][len(response["Appointments"]) - 1]
        if convert_datetime(task_data["startdateplan"], "Europe/Berlin") != convert_datetime(appointment["StartDateTime"]):
            update_data["START_DATE_PLAN"] = convert_datetime(appointment["StartDateTime"]) + "+02:00"
        if convert_datetime(task_data["enddateplan"], "Europe/Berlin") != convert_datetime(appointment["EndDateTime"]):
            update_data["END_DATE_PLAN"] = convert_datetime(appointment["EndDateTime"]) + "+02:00"
        if convert_datetime(task_data["deadline"], "Europe/Berlin") != convert_datetime(last_appointment["EndDateTime"]):
            update_data["DEADLINE"] = convert_datetime(last_appointment["EndDateTime"]) + "+02:00"
        new_leading = None
        contacts = {}
        local_appointments = []
        for appointment in response["Appointments"]:
            for contact in appointment.get("Contacts"):
                if contact.get("Email") not in contacts:
                    if contact.get("Email") == "mike.becker.kez@gmail.com":
                        contact["Email"] = "becker@korbacher-energiezentrum.de"
                    if contact.get("Email") == "niklas.koch.360@gmail.com":
                        contact["Email"] = "niklas.koch.e360@gmail.com"
                    contacts[contact.get("Email")] = contact
                    contacts[contact.get("Email")]["user"] = get_user_by_email(contact.get("Email"))
                    if contacts[contact.get("Email")]["user"] is None:
                        print("error user not found:", contact.get("Email"))
                    else:
                        if str(task_data["responsibleid"]) == str(contacts[contact.get("Email")]["user"]["ID"]):
                            new_leading = contact.get("Email")
                        else:
                            if new_leading is None and contact.get("JobTitle") in ["Elektriker", "Montage"]:
                                new_leading = contact.get("Email")
            bitrix_user_ids = []
            for contact in appointment.get("Contacts"):
                if contact.get("Email") in contacts and contacts[contact.get("Email")]["user"] is not None:
                    bitrix_user_ids.append(contacts[contact.get("Email")]["user"]["ID"])
                else:
                    print("email problem: ", contact.get("Email"))
            local_appointments.append({
                "StartDateTime": convert_datetime(appointment["StartDateTime"]) + "+02:00",
                "EndDateTime": convert_datetime(appointment["EndDateTime"]) + "+02:00",
                "bitrix_user_ids": bitrix_user_ids
            })
        if new_leading is not None:
            if task_data["responsibleid"] != contacts[new_leading]["user"]["ID"]:
                update_data["RESPONSIBLE_ID"] = contacts[new_leading]["user"]["ID"]
            del contacts[new_leading]
        supporting_users = []
        for contact in contacts.keys():
            if contact in contacts and contacts[contact]["user"] is not None:
                supporting_users.append(contacts[contact]["user"]["ID"])
            else:
                print("email problem: ", contact)
        new_support_users_list = persistent_users.data + list(set(supporting_users) - set(persistent_users.data))
        if set(task_data["accomplices"]) != set(new_support_users_list):
            update_data["ACCOMPLICES"] = new_support_users_list
        if len(update_data.keys()) > 0 or True:
            update_data["mfr_appointments"] = base64.b64encode(json.dumps(local_appointments).encode('utf-8')).decode('utf-8')
    if len(update_data.keys()) > 0:
        print(task_id, json.dumps(update_data, indent=2))
        update_task(task_id, update_data)


def run_cron_export():
    config = get_settings("external/mfr")
    print("<< BEGIN run cron export task mfr >>")
    if config is None:
        print("<< no config for export task mfr >>")
        return None
    last_task_export_time = config.get("last_task_export_time", "2021-01-01")
    tasks = get_tasks({
        "select": "full",
        "filter[>ACTIVITY_DATE]": last_task_export_time,
        "filter[%TITLE]": "[mfr]"
    }, force_reload=True)
    if tasks is None:
        print("<< tasks could not be loaded >>")
        return
    tasks2 = get_tasks({
        "select": "full",
        "filter[>CHANGED_DATE]": last_task_export_time,
        "filter[%TITLE]": "[mfr]"
    }, force_reload=True)
    if tasks2 is not None:
        for task in tasks2:
            found = next((item for item in tasks if item.get("id") == task.get("id")), None)
            if found is None:
                tasks.append(task)
    print("<< time: ", last_task_export_time, " >>")
    last_task_export_time = datetime.now()

    for task in tasks:
        comments = post_bitrix("task.commentitem.getlist", {
            "taskId": task.get("id")
        })
        if "result" in comments:
            task["comments"] = comments["result"]
        else:
            task["comments"] = []
        export_by_bitrix_id(task_data=task)
    config = get_settings("external/mfr")
    if config is not None:
        config["last_task_export_time"] = last_task_export_time.astimezone().isoformat()
    set_settings("external/mfr", config)


def export_by_bitrix_id(bitrix_id=None, task_data=None):
    if task_data is None:
        print(">> BEGIN run export mfr task", bitrix_id, " <<")
        task_data = get_task(bitrix_id, force_reload=True)
    else:
        bitrix_id = task_data.get("id")
        print(">> export mfr task ", bitrix_id, " <<")
    task_buffer = MfrExportBuffer.query.filter(MfrExportBuffer.task_id == str(bitrix_id)).first()
    if task_buffer is None:
        task_buffer = MfrExportBuffer(task_id=bitrix_id)
        task_buffer.data = {}
        db.session.add(task_buffer)
    changes_found = False
    if task_data.get('mfr_id') in [None, ""]:
        changes_found = True
    else:
        important_fields = ["comments", "description"]
        for field in important_fields:
            if json.dumps(task_buffer.data.get(field)) != json.dumps(task_data.get(field)):
                changes_found = True
                break
    if changes_found is False:
        print(">> no_change <<")
        return
    else:
        print(">> change detected <<")
    task_buffer.last_change = datetime.now()
    task_buffer.data = task_data
    db.session.commit()

    deal_data, contact_data, company_data = get_linked_data_by_task(task_data)
    if contact_data is not None and contact_data.get("mfr_id") in [None, "", "0"]:
        export_contact_by_bitrix_id(contact_data["id"])
        contact_data = get_contact(contact_data["id"], force_reload=True)
    else:
        if company_data is not None and company_data.get("mfr_id") in [None, "", "0"]:
            export_company_by_bitrix_id(company_data["id"])
            company_data = get_company(company_data["id"])
    if contact_data is None and company_data is None:
        print(">> no contact", bitrix_id, " <<")
        return
    post_data = get_export_data(task_data, contact_data, deal_data, company_data)
    documents = None
    comment_files = None
    if "documents" in post_data:
        documents = post_data["documents"]
        del post_data["documents"]
    if "comment_files" in task_data:
        comment_files = task_data["comment_files"]
        del task_data["comment_files"]
    if task_data.get("mfr_id", None) in ["", None, 0]:
        print(json.dumps(post_data, indent=2))
        response = post("/ServiceRequests", post_data=post_data)
        if response.get("Id") not in ["", None, 0]:
            task_data['mfr_id'] = response.get("Id")
            update_task(bitrix_id, {"mfr_id": response.get("Id")})
        else:
            print(json.dumps(response, indent=2))
    else:
        response = get(f"/ServiceRequests({task_data.get('mfr_id')}L)?$expand=ServiceObjects,Customer,Reports,Items,Appointments/Contacts,Steps,Comments,StockMovements", parameters={
            "id": task_data.get('mfr_id')
        })
        if response.get("State") not in [None, ""]:
            response["Description"] = post_data["Description"]
            response = put(f"/ServiceRequests({task_data.get('mfr_id')}L)", post_data=response)
    if documents is not None and task_data.get('mfr_id') not in [None, ""]:
        response = get(f"/ServiceRequests({task_data.get('mfr_id')}L)?$expand=ServiceObjects,Documents,Customer,Reports,Items,Appointments/Contacts,Steps,Comments,StockMovements", parameters={
            "id": task_data.get('mfr_id')
        })
        for document in documents:
            if document["TYPE"] != "file":
                continue
            existing_document = next((item for item in response.get("Documents", []) if item["FileName"] == str(document["NAME"])), None)
            if existing_document is None:
                file_content = get_file_content(document["ID"])
                mime_type = magic.from_buffer(file_content, mime=True)
                upload_response = post("/Document/UploadAndCreate", files=[
                    ("FilePath", (document["NAME"], file_content, mime_type))
                ], type="mfr")
                if 'DocumentDto' in upload_response and "Id" in upload_response.get('DocumentDto'):
                    response_document_attach = put(f"/ServiceRequest/{task_data.get('mfr_id')}/Document/{upload_response.get('DocumentDto').get('Id')}", type="mfr")
    if comment_files is not None and task_data.get('mfr_id') not in [None, ""]:
        response = get(f"/ServiceRequests({task_data.get('mfr_id')}L)?$expand=ServiceObjects,Documents,Customer,Reports,Items,Appointments/Contacts,Steps,Comments,StockMovements", parameters={
            "id": task_data.get('mfr_id')
        })
        for document in comment_files:
            existing_document = next((item for item in response.get("Documents", []) if item["FileName"] == str(document["NAME"])), None)
            if existing_document is None:
                file_content = get_file_content(url=f'https://keso.bitrix24.de{document["DOWNLOAD_URL"]}')
                mime_type = magic.from_buffer(file_content, mime=True)
                upload_response = post("/Document/UploadAndCreate", files=[
                    ("FilePath", (document["NAME"], file_content, mime_type))
                ], type="mfr")
                if 'DocumentDto' in upload_response and "Id" in upload_response.get('DocumentDto'):
                    response_document_attach = put(f"/ServiceRequest/{task_data.get('mfr_id')}/Document/{upload_response.get('DocumentDto').get('Id')}", type="mfr")
    if deal_data is not None and str(deal_data.get("category_id")) == "134":
        response = get(f"/ServiceRequests({task_data.get('mfr_id')}L)?$expand=ServiceObjects,Customer,Reports,Items,Appointments/Contacts,Steps,Comments,StockMovements", parameters={
            "id": str(task_data.get('mfr_id'))
        })
        if response is not None and len(response.get("Appointments", [])) == 0:
            response = post("/Appointments", post_data={
                "ServiceRequestId": str(task_data.get('mfr_id')),
                "State": "NotVisited",
                "StartDateTime": deal_data["service_appointment_startdate"],
                "EndDateTime": deal_data["service_appointment_enddate"],
                "ContactId": "18105040909"
            })
            response = put(f"/ServiceRequests({task_data.get('mfr_id')}L)", post_data={
                "Id": str(task_data.get('mfr_id')),
                "State": "Released"
            })


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
        deal_data = get_deal(deal_id, force_reload=True)
        if contact_id is None and company_id is None:
            if deal_data["contact_id"] not in [None, "", "0", 0]:
                contact_id = deal_data["contact_id"]
            else:
                if deal_data["company_id"] not in [None, "", "0", 0]:
                    company_id = deal_data["company_id"]
    if contact_id is not None:
        contact_data = get_contact(contact_id, force_reload=True)
        if contact_data["company_id"] not in [None, "", "0", 0]:
            company_data = get_company(contact_data["company_id"])
    else:
        if company_id is not None:
            company_data = get_company(company_id)
    if company_data is not None and company_data.get("street") in ["", 0, False, None]:
        company_data = None
    return deal_data, contact_data, company_data


def get_template_id_by_deal(deal_data):
    config = {
        "default": "17991565319",
        "electric": "17432084483",
        "service": "17991565318",
        "roof": "17991565317",
        "heating": "17996480515",
        "holiday": "17996480515",
        "roof_reconstruction_pv": "18134892576",
        "roof_reconstruction": "18145247234",
        "service_storage_pb": "18134892577",
        "service_storage_li": "18134892579",
        "service_pv_storage_li": "18147409921",
        "service_pv_storage_pb": "18147409922",
        "storage_swap": "18145247235",
        "repair_electric": "18137612317",
        "additional_roof": "18145247236",
        "solar_edge_change_test": "18147409920",
        "enpal_mvt": "18214387720",
        "enpal_verbau": "18214387721",
        "additional_electric": "18511986693",
        "aufmass_wp": "42852253735",
        "logistic": "43163254799",
        "wartung_waermepumpe": "47134933037",
        "vde_pruefung_elektrisch": "47134933038"
    }
    if deal_data is None:
        return config["default"]
    if deal_data.get("mfr_category", "") != "default" and deal_data.get("mfr_category", "") in config:
        return config[deal_data.get("mfr_category", "")]
    if deal_data is None:
        return config["default"]
    if deal_data.get("category_id", "") == "32":
        return config["electric"]
    if deal_data.get("category_id", "") == "1":
        return config["roof"]
    if deal_data.get("category_id", "") == "9":
        return config["heating"]
    if deal_data.get("category_id", "") == "134":
        return config["service"]
    return config["default"]
