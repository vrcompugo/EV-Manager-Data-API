from app import db
from sqlalchemy.ext.hybrid import hybrid_property
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields


class EEGRefundRate(db.Model):
    __tablename__ = "eeg_refund_rate"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    month = db.Column(db.Integer)
    year = db.Column(db.Integer)
    min_kwp = db.Column(db.Float)
    max_kwp = db.Column(db.Float)
    value = db.Column(db.Float)
