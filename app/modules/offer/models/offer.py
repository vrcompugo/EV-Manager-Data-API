from sqlalchemy.ext.hybrid import hybrid_property
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields
from enum import Enum

from app import db
from app.modules.customer.models.customer import CustomerSchema
from app.modules.reseller.models.reseller import ResellerSchema


class STATUSES(Enum):
    created = "created"
    sent_out = "sent_out"
    declined = "declined"
    accepted = "accepted"


class Offer(db.Model):
    __versioned__ = {}
    __tablename__ = "offer"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    product = db.relationship("Product")
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))
    customer = db.relationship("Customer")
    address_id = db.Column(db.Integer, db.ForeignKey("customer_address.id"))
    address = db.relationship("CustomerAddress")
    payment_account_id = db.Column(db.Integer, db.ForeignKey("customer_payment_account.id"))
    payment_account = db.relationship("CustomerPaymentAccount")
    reseller_id = db.Column(db.Integer, db.ForeignKey("reseller.id"))
    reseller = db.relationship("Reseller")
    survey_id = db.Column(db.Integer, db.ForeignKey("survey.id"))
    survey = db.relationship("Survey")
    datetime = db.Column(db.DateTime)
    status = db.Column(db.String(20))
    data = db.Column(db.JSON)
    calculation = db.Column(db.JSON)
    price_definition = db.Column(db.JSON)
    errors = db.Column(db.JSON)
    last_updated = db.Column(db.DateTime)

    @hybrid_property
    def search_query(self):
        return db.session.query(Offer)

    @hybrid_property
    def reseller_name(self):
        if self.reseller is not None:
            return self.reseller.name
        return None

    @hybrid_property
    def reseller_group(self):
        if self.reseller is not None:
            return self.reseller.group.name
        return None


class OfferSchema(ModelSchema):

    reseller_name = fields.String()
    reseller_group = fields.String()
    reseller = fields.Nested(ResellerSchema)
    customer = fields.Nested(CustomerSchema)
    versions = fields.Constant([])

    class Meta:
        model = Offer
