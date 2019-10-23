from sqlalchemy.dialects.postgresql import TEXT
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields

from app import db


class Email(db.Model):
    __tablename__ = "email"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))
    template_id = db.Column(db.Integer, db.ForeignKey("email_template.id"))
    status = db.Column(db.String(250))
    datetime = db.Column(db.DateTime)
    from_email = db.Column(db.String(60))
    from_name = db.Column(db.String(120))
    recipients = db.Column(db.JSON)
    cc = db.Column(db.JSON)
    bcc = db.Column(db.JSON)
    subject = db.Column(db.String(250))
    html_body = db.Column(TEXT)
    text_body = db.Column(TEXT)
    attachments = db.Column(db.JSON)


class EmailSchema(ModelSchema):

    versions = fields.Constant([])

    class Meta:
        model = Email
