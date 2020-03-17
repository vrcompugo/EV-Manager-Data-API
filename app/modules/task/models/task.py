from sqlalchemy.ext.hybrid import hybrid_property
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields

from app import db

association_table = db.Table(
    'task_member_association',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('task_id', db.Integer, db.ForeignKey('task.id'))
)


class Task(db.Model):
    __tablename__ = "task"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer(), db.ForeignKey('customer.id'))
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'))
    reseller_id = db.Column(db.Integer(), db.ForeignKey('reseller.id'))
    order_id = db.Column(db.Integer(), db.ForeignKey('order.id'))
    remote_id = db.Column(db.Integer())
    label = db.Column(db.String(250))
    salutation = db.Column(db.String(30))
    title = db.Column(db.String(30))
    firstname = db.Column(db.String(100))
    lastname = db.Column(db.String(100))
    company = db.Column(db.String(100))
    street = db.Column(db.String(100))
    street_nb = db.Column(db.String(80))
    zip = db.Column(db.String(20))
    city = db.Column(db.String(60))
    distance_km = db.Column(db.Float())
    travel_time_minutes = db.Column(db.Integer())
    lat = db.Column(db.Float())
    lng = db.Column(db.Float())
    distance_km = db.Column(db.Integer())
    travel_time_minutes = db.Column(db.Integer())
    type = db.Column(db.String(40))
    deadline = db.Column(db.DateTime())
    begin = db.Column(db.DateTime())
    end = db.Column(db.DateTime())
    comment = db.Column(db.Text())
    status = db.Column(db.String(30))
    members = db.relationship("User", secondary=association_table)

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
        return db.session.query(Task)

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
    customer = fields.Nested("CustomerSchema")
    role = fields.Nested("UserRoleShortSchema")
    survey = fields.Nested("SurveySchema")
    versions = fields.Constant([])

    class Meta:
        model = Task
