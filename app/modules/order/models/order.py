from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.postgresql import TEXT
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields

from app import db


class Order(db.Model):
    __versioned__ = {}
    __tablename__ = "order"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    datetime = db.Column(db.DateTime())
    lead_number = db.Column(db.String(20))
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))
    customer = db.relationship("Customer")
    reseller_id = db.Column(db.Integer, db.ForeignKey("reseller.id"))
    reseller = db.relationship("Reseller")
    value_net = db.Column(db.Numeric(scale=4, precision=12))
    last_update = db.Column(db.DateTime)
    contact_source = db.Column(db.String(80))
    status = db.Column(db.String(20))
    commissions = db.Column(db.JSON)
    commission_value_net = db.Column(db.Numeric(scale=4, precision=12))

    @hybrid_property
    def search_query(self):
        return db.session.query(Order)


class OrderSchema(ModelSchema):

    versions = fields.Constant([])

    class Meta:
        model = Order
