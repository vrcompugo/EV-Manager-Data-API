from app import db
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields
from sqlalchemy.ext.hybrid import hybrid_property


class CalendarEvent(db.Model):
    __versioned__ = {}
    __tablename__ = "calendar_event"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer(), db.ForeignKey('customer.id'))
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'))
    reseller_id = db.Column(db.Integer(), db.ForeignKey('reseller.id'))
    order_id = db.Column(db.Integer(), db.ForeignKey('order.id'))
    task_id = db.Column(db.Integer(), db.ForeignKey('task.id'))
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

    class Meta:
        model = CalendarEvent
