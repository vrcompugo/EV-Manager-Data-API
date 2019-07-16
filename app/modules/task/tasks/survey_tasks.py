import datetime

from app import db
from app.models import UserRole
from app.modules.survey.models.survey import Survey, DATA_STATUSES, OFFER_STATUSES

from ..task_services import update_task_list
from ..models.task import Task


def update_tasks_by_survey(survey):

    old_task_list = db.session.query(Task).filter(Task.survey_id == survey.id).all()

    sales_role = db.session.query(UserRole).filter(UserRole.code == "sales").one()
    sales_lead_role = db.session.query(UserRole).filter(UserRole.code == "sales_lead").one()
    
    tasks = []
    if survey.data_status == DATA_STATUSES.INCOMPLETE.value:
        tasks.append({
            "datetime": survey.datetime,
            "link": "survey",
            "action": "complete-survey",
            "description": u"Aufnahmebogen vervollständigen",
            "customer_id": survey.customer_id,
            "user_id": survey.reseller.user_id,
            "role_id": sales_role.id,
            "reseller_id": survey.reseller_id,
            "survey_id": survey.id
        })
    if survey.data_status == DATA_STATUSES.MISSING_DATA.value:
        tasks.append({
            "datetime": survey.last_updated,
            "link": "survey",
            "action": "add-missing-data",
            "description": u"Fehlende Unterlagen/Daten nachtragen",
            "customer_id": survey.customer_id,
            "user_id": survey.reseller.user_id,
            "role_id": sales_role.id,
            "reseller_id": survey.reseller_id,
            "survey_id": survey.id
        })
        tasks.append({
            "datetime": survey.last_updated,
            "link": "survey",
            "reminder_datetime": survey.last_updated + datetime.timedelta(days=5),
            "action": "remind-missing-data",
            "description": "Verkäufer an fehlende Unterlagen erinnern",
            "customer_id": survey.customer_id,
            "role_id": sales_lead_role.id,
            "reseller_id": survey.reseller_id,
            "survey_id": survey.id
        })
    if survey.data_status == DATA_STATUSES.COMPLETE.value:
        if survey.offer_status == OFFER_STATUSES.OPEN.value:
            tasks.append({
                "datetime": survey.last_updated,
                "link": "survey",
                "action": "create-offer",
                "description": "Angebot erzeugen",
                "customer_id": survey.customer_id,
                "role_id": sales_lead_role.id,
                "reseller_id": survey.reseller_id,
                "survey_id": survey.id
            })

    update_task_list(old_task_list=old_task_list, new_task_list=tasks)
