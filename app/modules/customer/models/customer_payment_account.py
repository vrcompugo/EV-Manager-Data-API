from app import db
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property


class CustomerPaymentAccount(db.Model):
    __versioned__ = {}
    __tablename__ = "customer_payment_account"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer(), db.ForeignKey('customer.id'))
    address_id = db.Column(db.Integer(), db.ForeignKey('customer_address.id'))
    address = db.relationship("CustomerAddress")
    type = db.Column(db.String(30))
    data = db.Column(JSONB)

