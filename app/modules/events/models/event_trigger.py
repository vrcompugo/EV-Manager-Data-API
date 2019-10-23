from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields

from app import db


class EventTrigger(db.Model):
    __versioned__ = {}
    __tablename__ = "event_trigger"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    datetime = db.Column(db.DateTime)
    name = db.Column(db.String(50))
    data = db.Column(db.JSON)
    error = db.Column(db.Text)
    status = db.Column(db.String(30))


class EventTriggerSchema(ModelSchema):

    versions = fields.Constant([])

    class Meta:
        model = EventTrigger
