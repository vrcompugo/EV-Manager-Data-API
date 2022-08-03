from app import db
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.postgresql import JSONB
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields
from app.basemodel import BaseModel


class InvoiceBundleItem(BaseModel, db.Model):
    __tablename__ = "invoice_bundle_item"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    invoice_bundle_id = db.Column(db.Integer, db.ForeignKey("invoice_bundle.id"))
    datetime = db.Column(db.DateTime)
    contract_number = db.Column(db.String(150))
    invoice_number = db.Column(db.String(150))
    customer_number = db.Column(db.String(150))
    customer_name = db.Column(db.String(150))
    customer_street = db.Column(db.String(250))
    customer_zip = db.Column(db.String(20))
    customer_city = db.Column(db.String(150))
    total_net = db.Column(db.Numeric(scale=4, precision=12))
    total = db.Column(db.Numeric(scale=4, precision=12))
    source = db.Column(db.String(150))
