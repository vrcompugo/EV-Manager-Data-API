import json
import datetime
from sqlalchemy import func, or_, and_

from app import db
from app.modules.external.bitrix24.lead import get_lead, update_lead
from app.modules.external.bitrix24.contact import get_contact, update_contact

from .models.user_zip_association import UserZipAssociation


def auto_assign_lead_to_user(lead_id):
    lead_data = get_lead(lead_id)
    if "assigned_by_id" not in lead_data or (lead_data["assigned_by_id"] not in ["106", "41", "344"]):
        return None
    if "contact_id" not in lead_data or lead_data["contact_id"] is None or int(lead_data["contact_id"]) == 0:
        return None

    contact_data = get_contact(lead_data["contact_id"])
    if "zip" not in contact_data or contact_data["zip"] is None or contact_data["zip"] == "":
        return None
    contact_data["zip"] = contact_data["zip"].strip()
    current_cycle_index = int(datetime.datetime.now().strftime("%V"))
    user = UserZipAssociation.query\
        .filter(UserZipAssociation.last_assigned.is_(None))\
        .filter(or_(
            and_(
                UserZipAssociation.current_cycle_index == current_cycle_index,
                UserZipAssociation.current_cycle_count <= UserZipAssociation.max_leads
            ),
            UserZipAssociation.current_cycle_index != current_cycle_index,
            UserZipAssociation.current_cycle_index.is_(None)
        ))\
        .filter(UserZipAssociation.max_leads > 0)\
        .filter(UserZipAssociation.data.contains([contact_data['zip']]))
    user = user.first()
    if user is None:
        user = UserZipAssociation.query\
            .filter(or_(
                and_(
                    UserZipAssociation.current_cycle_index == current_cycle_index,
                    UserZipAssociation.current_cycle_count <= UserZipAssociation.max_leads
                ),
                UserZipAssociation.current_cycle_index != current_cycle_index,
                UserZipAssociation.current_cycle_index.is_(None)
            ))\
            .filter(UserZipAssociation.max_leads > 0)\
            .filter(UserZipAssociation.data.contains([contact_data['zip']]))\
            .order_by(UserZipAssociation.last_assigned.asc())\
            .first()
    if user is None:
        update_data = {"assigned_by_id": 344}
    else:
        update_data = {"assigned_by_id": user.user_id}
    update_lead(lead_id, update_data)
    update_contact(lead_data["contact_id"], update_data)
    if user is not None:
        if user.current_cycle_index is None or user.current_cycle_index != current_cycle_index:
            user.current_cycle_index = current_cycle_index
            user.current_cycle_count = 0
        user.current_cycle_count = user.current_cycle_count + 1
        user.last_assigned = datetime.datetime.now()
        db.session.commit()
