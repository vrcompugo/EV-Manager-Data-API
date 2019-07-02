from sqlalchemy.ext.hybrid import hybrid_property
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields

from app import db
from app.modules.customer.models.customer import CustomerSchema
from app.modules.user.models.user_role import UserRoleShortSchema

class Survey(db.Model):
    __versioned__ = {}
    __tablename__ = "survey"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))
    customer = db.relationship("Customer")
    address_id = db.Column(db.Integer, db.ForeignKey("customer_address.id"))
    reseller_id = db.Column(db.Integer, db.ForeignKey("reseller.id"))
    reseller = db.relationship("Reseller")
    datetime = db.Column(db.DateTime)
    offer_until = db.Column(db.Date)
    last_updated = db.Column(db.DateTime)
    data = db.Column(db.JSON)

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

    @hybrid_property
    def lead_number(self):
        if self.customer is not None:
            return self.customer.lead_number
        return None

    @hybrid_property
    def customer_number(self):
        if self.customer is not None:
            return self.customer.customer_number
        return None


class SurveySchema(ModelSchema):

    lead_number = fields.String()
    customer_number = fields.String()
    reseller_name = fields.String()
    reseller_group = fields.String()
    customer = fields.Nested(CustomerSchema)
    versions = fields.Constant([])

    class Meta:
        model = Survey
