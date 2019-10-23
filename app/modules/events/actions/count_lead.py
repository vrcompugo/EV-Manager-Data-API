from app import db
from app.models import Lead, Reseller
from app.exceptions import ApiException


def count_lead(trigger, action):
    if "lead_id" not in trigger.data:
        raise ApiException(code="not-found", message="lead id not given", http_status=404)
    lead = db.session.query(Lead).filter(Lead.id == trigger.data["lead_id"]).first()
    if lead is None:
        raise ApiException(code="not-found", message="Lead not found", http_status=404)
    reseller = lead.reseller
    if reseller is None:
        raise ApiException(code="not-found", message="Reseller not found", http_status=404)

    if reseller.lead_balance is None:
        reseller.lead_balance = 0

    if trigger.name == "lead_exported":
        if "operation" not in trigger.data:
            raise ApiException(code="not-found", message="Operation not given", http_status=404)
        if "source" not in trigger.data:
            raise ApiException(code="not-found", message="source not given", http_status=404)
        if trigger.data["source"] == "nocrm.io" and trigger.data["operation"] == "add":
            reseller.lead_balance = reseller.lead_balance + 1
            db.session.commit()
    else:
        if "old_data" in trigger.data and "new_data" in trigger.data:
            if "status" in trigger.data["new_data"]:
                if "status" not in trigger.data["old_data"] or trigger.data["old_data"]["status"] != trigger.data["new_data"]["status"]:
                    if trigger.data["new_data"]["status"] == "won":
                        reseller.lead_balance = reseller.lead_balance - 8
                        db.session.commit()
