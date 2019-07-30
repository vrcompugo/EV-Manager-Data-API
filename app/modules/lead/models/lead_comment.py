from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.postgresql import TEXT
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields

from app import db
from app.modules.customer.models.customer import CustomerSchema


class LeadComment(db.Model):
    __versioned__ = {}
    __tablename__ = "lead_comments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("lead.id"))
    lead = db.relationship("Lead")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    change_to_offer_created = db.Column(db.Boolean())
    datetime = db.Column(db.DateTime())
    comment = db.Column(TEXT)
    attachments = db.Column(db.JSON)


class LeadCommentSchema(ModelSchema):

    versions = fields.Constant([])

    class Meta:
        model = LeadComment
