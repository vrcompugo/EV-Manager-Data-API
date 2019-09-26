from sqlalchemy.dialects.postgresql import TEXT
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields

from app import db


class EMailTemplate(db.Model):
    __versioned__ = {}
    __tablename__ = "email_template"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(60))
    from_email = db.Column(db.String(60))
    from_name = db.Column(db.String(120))
    cc = db.Column(db.JSON)
    bcc = db.Column(db.JSON)
    subject = db.Column(db.String(120))
    html_body = db.Column(TEXT)
    text_body = db.Column(TEXT)
    attachments = db.Column(db.JSON)


class EMailTemplateSchema(ModelSchema):

    versions = fields.Constant([])

    class Meta:
        model = EMailTemplate
