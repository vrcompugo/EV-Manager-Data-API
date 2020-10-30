from app import db
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.postgresql import JSONB
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields


class QuoteHistory(db.Model):
    __tablename__ = "quote_history"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lead_id = db.Column(db.Integer)
    datetime = db.Column(db.DateTime)
    label = db.Column(db.String(120))
    data = db.Column(JSONB)
