from sqlalchemy.ext.hybrid import hybrid_property
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields

from app import db
from app.modules.customer.models.customer import CustomerSchema
from app.modules.user.models.user_role import UserRoleShortSchema


class Lead(db.Model):
    __versioned__ = {}
    __tablename__ = "lead"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    number = db.Column(db.String(20))
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))
    customer = db.relationship("Customer")
    address_id = db.Column(db.Integer, db.ForeignKey("customer_address.id"))
    address = db.relationship("CustomerAddress")
    reseller_id = db.Column(db.Integer, db.ForeignKey("reseller.id"))
    reseller = db.relationship("Reseller")
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"))
    project = db.relationship("Project")
    value = db.Column(db.Numeric(scale=4, precision=12))
    last_update = db.Column(db.DateTime)
    status = db.Column(db.String(20))
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
    def customer_number(self):
        if self.customer is not None:
            return self.customer.customer_number
        return None


class LeadSchema(ModelSchema):

    lead_number = fields.String()
    customer_number = fields.String()
    reseller_name = fields.String()
    reseller_group = fields.String()
    customer = fields.Nested(CustomerSchema)
    versions = fields.Constant([])

    class Meta:
        model = Lead
