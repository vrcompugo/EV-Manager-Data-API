from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields
from sqlalchemy.dialects.postgresql.json import JSONB

from app import db


class EventAction(db.Model):
    __versioned__ = {}
    __tablename__ = "event_action"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    triggers = db.Column(JSONB)
    action = db.Column(db.String(50))
    ordering = db.Column(db.Integer)
    conditions = db.Column(db.JSON)
    config = db.Column(db.JSON)


class EventActionSchema(ModelSchema):

    versions = fields.Constant([])

    class Meta:
        model = EventAction
