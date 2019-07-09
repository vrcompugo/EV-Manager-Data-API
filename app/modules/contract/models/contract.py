from sqlalchemy.ext.hybrid import hybrid_property
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields

from app import db
from app.modules.user.models.user_role import UserRoleShortSchema


class Contract(db.Model):
    __versioned__ = {}
    __tablename__ = "contract"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    number = db.Column(db.String(20))
    offer_id = db.Column(db.Integer, db.ForeignKey("offer.id"))
    offer = db.relationship("Offer")
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))
    customer = db.relationship("Customer")
    address_id = db.Column(db.Integer, db.ForeignKey("customer_address.id"))
    address = db.relationship("CustomerAddress")
    payment_account_id = db.Column(db.Integer, db.ForeignKey("customer_payment_account.id"))
    payment_account = db.relationship("CustomerPaymentAccount")
    reseller_id = db.Column(db.Integer, db.ForeignKey("reseller.id"))
    reseller = db.relationship("Reseller")
    datetime = db.Column(db.DateTime)
    status = db.Column(db.String(20))
    data = db.Column(db.JSON)
    calculation = db.Column(db.JSON)
    price_definition = db.Column(db.JSON)
    errors = db.Column(db.JSON)
    last_updated = db.Column(db.DateTime)


class ContractSchema(ModelSchema):

    versions = fields.Constant([])

    class Meta:
        model = Contract
