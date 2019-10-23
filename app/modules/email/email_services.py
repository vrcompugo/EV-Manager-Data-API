import datetime
import time
from flask import render_template_string
from flask_emails import Message
from io import StringIO

from app import db
from app.config import email_config
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict
from app.utils.ml_stripper import MLStripper
from app.models import S3File

from .models.email import Email
from .models.email_template import EMailTemplate, EMailTemplateSchema


def add_item(data):
    new_item = EMailTemplate()
    new_item = set_attr_by_dict(new_item, data, ["id", "activities"])
    db.session.add(new_item)
    db.session.commit()
    return new_item


def update_item(id, data):
    item = db.session.query(EMailTemplate).get(id)
    if item is not None:
        item = set_attr_by_dict(item, data, ["id", "activities"])
        db.session.commit()
        return item
    else:
        raise ApiException("item_doesnt_exist", "Item doesn't exist.", 409)


def get_items(tree, sort, offset, limit, fields):
    return get_items_by_model(EMailTemplate, EMailTemplateSchema, tree, sort, offset, limit, fields)


def get_one_item(id, fields = None):
    return get_one_item_by_model(EMailTemplate, EMailTemplateSchema, id, fields)


def generate_email(template_code, data):
    email_template = db.session.query(EMailTemplate).filter(EMailTemplate.code == template_code).first()
    if email_template is None:
        raise ApiException("item_doesnt_exist", "Email template doesn't exist.", 409)
    subject = render_template_string(email_template.subject, **data)
    html_body = render_template_string(email_template.html_body, **data)
    if email_template.text_body is None:
        s = MLStripper()
        s.feed(html_body)
        text_body = s.get_data()
    else:
        text_body = render_template_string(email_template.text_body, **data)

    email = Email(
        status="created",
        template_id=email_template.id,
        datetime=datetime.datetime.now(),
        from_email=email_template.from_email,
        from_name=email_template.from_name,
        bcc=email_template.bcc,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        attachments=email_template.attachments
    )
    if "customer_id" in data:
        email.customer_id = data["customer_id"]
    db.session.add(email)
    return email


def send_email(email):

    message = Message(text=email.text_body,
                      html=email.html_body,
                      subject=email.subject,
                      mail_from=(email.from_name, email.from_email),
                      config=email_config)

    for file in email.attachments:
        s3_file = db.session.query(S3File).get(file["id"])
        file_stream = StringIO(s3_file.get_file())
        message.attach(data=file_stream, filename=file.filename)

    try:
        for recipient in email.bcc:
            message.mail_to = recipient
            message.send()
            time.sleep(3)
        message.mail_to = email.recipients
        message.cc = email.cc
        r = message.send()
        time.sleep(5)

        if r.status_code not in [250, ]:
            email.status = "error"
        else:
            email.status = "sent"
    except Exception as e:
        email.status = "error" + str(e)

    db.session.commit()
    return email
