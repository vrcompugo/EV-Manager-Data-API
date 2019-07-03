from sqlalchemy.ext.hybrid import hybrid_property
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields

from app import db
from app.modules.customer.models.customer import CustomerSchema
from app.modules.user.models.user_role import UserRoleShortSchema

class Task(db.Model):
    __versioned__ = {}
    __tablename__ = "task"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    datetime = db.Column(db.DateTime)
    reminder_datetime = db.Column(db.DateTime)
    description = db.Column(db.String(255))
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))
    customer = db.relationship("Customer")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User")
    role_id = db.Column(db.Integer, db.ForeignKey("user_role.id"))
    role = db.relationship("UserRole")
    reseller_id = db.Column(db.Integer, db.ForeignKey("reseller.id"))
    reseller = db.relationship("Reseller")
    survey_id = db.Column(db.Integer, db.ForeignKey("survey.id"))
    survey = db.relationship("Survey")
    offer_id = db.Column(db.Integer, db.ForeignKey("offer.id"))
    offer = db.relationship("Offer")
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"))
    project = db.relationship("Project")
    contract_id = db.Column(db.Integer, db.ForeignKey("contract.id"))
    contract = db.relationship("Contract")
    pv_system_id = db.Column(db.Integer, db.ForeignKey("pv_system.id"))
    pv_system = db.relationship("PVSystem")
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    product = db.relationship("Product")

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

    @hybrid_property
    def project_number(self):
        if self.project is not None:
            return self.project.number
        return None

    @hybrid_property
    def contract_number(self):
        if self.contract is not None:
            return self.contract.number
        return None


class TaskSchema(ModelSchema):

    lead_number = fields.String()
    customer_number = fields.String()
    project_number = fields.String()
    contract_number = fields.String()
    role = fields.Nested(UserRoleShortSchema)
    customer = fields.Nested(CustomerSchema)
    versions = fields.Constant([])

    class Meta:
        model = Task
