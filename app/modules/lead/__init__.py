

def cron():
    from sqlalchemy import not_

    from app import db

    from .models import Lead, LeadComment

    leads = db.session().query(Lead).filter(Lead.id > 12664)\
        .filter(Lead.reseller_id > 0)\
        .filter(Lead.status == "new")\
        .filter(not_(Lead.comments.any(code="welcome_email")))
    print(leads)
