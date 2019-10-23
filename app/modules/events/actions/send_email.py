from app.models import EMailTemplate


def send_email(trigger, action):
    if "template" not in action.config:
        raise Exception("no template given")
    template = EMailTemplate.query.filter(EMailTemplate.code == action.config["template"]).first()
    if template is None:
        raise Exception("template not found")

    if template.code == "lead_welcome_email":
        from app.models import Lead
        from app.modules.lead.lead_services import send_welcome_email
        if "lead_id" not in trigger.data:
            raise Exception("lead id not given")
        lead = Lead.query.filter(Lead.id == trigger.data["lead_id"]).first()
        if lead is None:
            raise Exception("lead not found")
        send_welcome_email(lead)

