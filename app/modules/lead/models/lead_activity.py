from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.postgresql import TEXT
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields

from app import db


class LeadActivity(db.Model):
    __versioned__ = {}
    __tablename__ = "lead_activity"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("lead.id"))
    lead = db.relationship("Lead", backref="activities")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    datetime = db.Column(db.DateTime())
    action = db.Column(db.String(80))
    action_data = db.Column(db.JSON)


class LeadActivitySchema(ModelSchema):

    versions = fields.Constant([])

    class Meta:
        model = LeadActivity
