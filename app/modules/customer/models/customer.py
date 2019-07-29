from app import db
from sqlalchemy.ext.hybrid import hybrid_property
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields


class Customer(db.Model):
    __versioned__ = {}
    __tablename__ = "customer"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_number = db.Column(db.String(30), unique=True)
    lead_number = db.Column(db.String(30), unique=True)
    company = db.Column(db.String(100))
    salutation = db.Column(db.String(30))
    title = db.Column(db.String(30))
    firstname = db.Column(db.String(100))
    lastname = db.Column(db.String(100))
    email = db.Column(db.String(120))
    pending_email = db.Column(db.String(120))
    email_status = db.Column(db.String(20))
    last_change = db.Column(db.DateTime)
    default_address_id = db.Column(db.Integer, db.ForeignKey('customer_address.id', use_alter=True))
    default_address = db.relationship("CustomerAddress", foreign_keys=[default_address_id], post_update=True)
    default_payment_account_id = db.Column(db.Integer, db.ForeignKey('customer_payment_account.id', use_alter=True))
    default_payment_account = db.relationship("CustomerPaymentAccount", foreign_keys=[default_payment_account_id], post_update=True)

    @hybrid_property
    def search_query(self):
        return db.session.query(Customer)

class CustomerSchema(ModelSchema):

    versions = fields.Constant([])

    class Meta:
        model = Customer
