from app import db
from marshmallow_sqlalchemy import ModelSchema
from marshmallow_sqlalchemy.fields import Nested
from marshmallow import fields
from sqlalchemy.ext.hybrid import hybrid_property

from app.modules.task.models.task import TaskSchema
from app.modules.reseller.models.reseller import ResellerSchema
from app.modules.user.models.user import UserSchema
from app.modules.order.models.order import OrderSchema
from app.modules.customer.models.customer import CustomerSchema


class CalendarEvent(db.Model):
    __versioned__ = {}
    __tablename__ = "calendar_event"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer(), db.ForeignKey('customer.id'))
    customer = db.relationship("Customer")
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'))
    user = db.relationship("User")
    reseller_id = db.Column(db.Integer(), db.ForeignKey('reseller.id'))
    reseller = db.relationship("Reseller")
    order_id = db.Column(db.Integer(), db.ForeignKey('order.id'))
    order = db.relationship("Order")
    task_id = db.Column(db.Integer(), db.ForeignKey('task.id'))
    task = db.relationship("Task")
    color = db.Column(db.String(10))
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


class CalendarEventSchema(ModelSchema):

    versions = fields.Constant([])
    customer_id = fields.Integer()
    user_id = fields.Integer()
    reseller_id = fields.Integer()
    task_id = fields.Integer()
    order_id = fields.Integer()
    location = fields.String()
    customer = Nested(CustomerSchema, many=False)
    task = Nested(TaskSchema, many=False)
    reseller = Nested(ResellerSchema, many=False)
    order = Nested(OrderSchema, many=False)

    class Meta:
        model = CalendarEvent
