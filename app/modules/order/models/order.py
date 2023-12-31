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
    label = db.Column(db.String(200))
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))
    customer = db.relationship("Customer")
    reseller_id = db.Column(db.Integer, db.ForeignKey("reseller.id"))
    reseller = db.relationship("Reseller")
    offer_id = db.Column(db.Integer, db.ForeignKey("offer_v2.id"))
    offer = db.relationship("OfferV2")
    contract_number = db.Column(db.String(120))
    category = db.Column(db.String(80))
    type = db.Column(db.String(60))
    street = db.Column(db.String(90))
    street_nb = db.Column(db.String(20))
    zip = db.Column(db.String(20))
    city = db.Column(db.String(60))
    lat = db.Column(db.Float())
    lng = db.Column(db.Float())
    data = db.Column(db.JSON)
    value_net = db.Column(db.Numeric(scale=4, precision=12))
    last_update = db.Column(db.DateTime)
    contact_source = db.Column(db.String(80))
    status = db.Column(db.String(20))
    commissions = db.Column(db.JSON)
    commission_value_net = db.Column(db.Numeric(scale=4, precision=12))
    is_checked = db.Column(db.Boolean)
    is_paid = db.Column(db.Boolean)

    @hybrid_property
    def location(self):
        data = []
        if self.street is not None:
            data.append(self.street)
        if self.street_nb is not None:
            data.append(self.street_nb)
        if self.zip is not None:
            data.append(self.zip)
        if self.city is not None:
            data.append(self.city)
        return " ".join(data)

    @hybrid_property
    def search_query(self):
        return db.session.query(Order)

    @hybrid_property
    def fulltext(self):
        return (
            Order.category + " "
            + Order.label
        )


class OrderSchema(ModelSchema):

    versions = fields.Constant([])
    value_net = fields.Float()
    commission_value_net = fields.Float()

    class Meta:
        model = Order
