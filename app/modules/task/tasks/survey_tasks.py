from datetime import datetime

from app import db
from app.models import UserRole
from app.modules.survey.models.survey import Survey, DATA_STATUSES, OFFER_STATUSES

from ..task_services import add_item, delete_items_except


def update_tasks_by_survey(survey):
    survey_tasks = db.session.query(Survey).filter(Survey.id == survey.id).all()
    sales_role = db.session.query(UserRole).filter(UserRole.code == "sales").one()
    sales_lead_role = db.session.query(UserRole).filter(UserRole.code == "sales_lead").one()
    excepted_tasks = []
    if survey.data_status == DATA_STATUSES.INCOMPLETE.value:
        excepted_tasks.append(add_item({
            "datetime": survey.last_updated,
            "description": u"Aufnahmebogen vervollständigen",
            "customer_id": survey.customer_id,
            "user_id": survey.reseller.user_id,
            "role_id": sales_role.id,
            "reseller_id": survey.reseller_id,
            "survey_id": survey.id
        }))
    if survey.data_status == DATA_STATUSES.COMPLETE.value:
        if survey.offer_status == OFFER_STATUSES.OPEN.value:
            excepted_tasks.append(add_item({
                "datetime": survey.last_updated,
                "description": "Angebot erzeugen",
                "customer_id": survey.customer_id,
                "role_id": sales_lead_role.id,
                "reseller_id": survey.reseller_id,
                "survey_id": survey.id
            }))
        if survey.offer_status == OFFER_STATUSES.MISSING_DATA.value:
            excepted_tasks.append(add_item({
                "datetime": survey.last_updated,
                "description": "Unterlagen fehlen",
                "customer_id": survey.customer_id,
                "user_id": survey.reseller.user_id,
                "role_id": sales_role.id,
                "reseller_id": survey.reseller_id,
                "survey_id": survey.id
            }))
            excepted_tasks.append(add_item({
                "datetime": survey.last_updated,
                "description": "Fehlende Unterlagen anfragen",
                "customer_id": survey.customer_id,
                "role_id": sales_lead_role.id,
                "reseller_id": survey.reseller_id,
                "survey_id": survey.id
            }))
    delete_items_except(survey_tasks, excepted_tasks)
