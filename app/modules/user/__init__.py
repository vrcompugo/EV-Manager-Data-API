import json
import datetime
from sqlalchemy import func, or_, and_

from app import db
from app.modules.external.bitrix24.deal import get_deal, update_deal
from app.modules.external.bitrix24.contact import get_contact, update_contact

from .models.user_zip_association import UserZipAssociation


def auto_assign_lead_to_user(deal_id):
    deal_data = get_deal(deal_id)
    if "assigned_by_id" not in deal_data or deal_data["assigned_by_id"] != "17":
        return None
    if "contact_id" not in deal_data or deal_data["contact_id"] is None or int(deal_data["contact_id"]) == 0:
        return None

    contact_data = get_contact(deal_data["contact_id"])
    if "zip" not in contact_data or contact_data["zip"] is None or contact_data["zip"] == "":
        return None

    current_cycle_index = int(datetime.datetime.now().month)
    user = UserZipAssociation.query\
        .filter(UserZipAssociation.last_assigned.is_(None))\
        .filter(or_(
            and_(
                UserZipAssociation.current_cycle_index == current_cycle_index,
                UserZipAssociation.current_cycle_count < UserZipAssociation.max_leads
            ),
            UserZipAssociation.current_cycle_index != current_cycle_index,
            UserZipAssociation.current_cycle_index.is_(None)
        ))\
        .filter(UserZipAssociation.data.contains([contact_data['zip']]))
    user = user.first()
    if user is None:
        user = UserZipAssociation.query\
            .filter(or_(
                and_(
                    UserZipAssociation.current_cycle_index == current_cycle_index,
                    UserZipAssociation.current_cycle_count < UserZipAssociation.max_leads
                ),
                UserZipAssociation.current_cycle_index != current_cycle_index,
                UserZipAssociation.current_cycle_index.is_(None)
            ))\
            .filter(UserZipAssociation.data.contains([contact_data['zip']]))\
            .order_by(UserZipAssociation.last_assigned.asc())\
            .first()
    if user is None:
        update_data = {"assigned_by_id": 1}
    else:
        update_data = {"assigned_by_id": user.user_id}
    update_deal(deal_id, update_data)
    update_contact(deal_data["contact_id"], update_data)
    if user is not None:
        if user.current_cycle_index != current_cycle_index:
            user.current_cycle_index = current_cycle_index
            user.current_cycle_count = 0
        user.current_cycle_count = user.current_cycle_count + 1
        user.last_assigned = datetime.datetime.now()
        db.session.commit()
