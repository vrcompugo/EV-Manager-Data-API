import os


def cron():
    if os.getenv('ENVIRONMENT') != "prod":
        return
    from sqlalchemy import not_

    from app import db
    from app.modules.importer.sources.nocrm_io.lead import run_export, find_association

    from .models import Lead, LeadComment
    from .lead_services import send_welcome_email

    rows = db.engine.execute("select * from "
                             "lead left join ("
                                "select * from import_id_association where source = 'nocrm.io' and model = 'Lead'"
                             ") as link on link.local_id = lead.id "
                             "where lead.id > 12664 and link.id is null")

    for row in rows:
        run_export(local_id=row[0])
        print("export ", row[0])

    leads = db.session().query(Lead).filter(Lead.id > 12664)\
        .filter(Lead.reseller_id > 0)\
        .filter(Lead.status == "new")\
        .filter(not_(Lead.comments.any(code="welcome_email"))).all()
    for lead in leads:
        association = find_association(model="Lead", local_id=lead.id)
        if association is not None:
            send_welcome_email(lead)
            print("send_welcome ", lead.id)
