

def cron():
    from sqlalchemy import not_

    from app import db
    from app.modules.importer.sources.nocrm_io.lead import run_export
    from app.modules.importer.models.import_id_association import ImportIdAssociation

    from .models import Lead, LeadComment

    rows = db.engine.execute("select * from "
                             "lead left join ("
                                "select * from import_id_association where source = 'nocrm.io' and model = 'Lead'"
                             ") as link on link.local_id = lead.id "
                             "where lead.id > 12664 and link.id is null")

    for row in rows:
        #run_export(local_id=lead.id)
        print("export ", row[0])

    leads = db.session().query(Lead).filter(Lead.id > 12664)\
        .filter(Lead.reseller_id > 0)\
        .filter(Lead.status == "new")\
        .filter(not_(Lead.comments.any(code="welcome_email"))).all()
    for lead in leads:
        print("send_welcome ", lead.id)
