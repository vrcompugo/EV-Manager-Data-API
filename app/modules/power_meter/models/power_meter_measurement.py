
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields

from app import db


class PowerMeterMeasurement(db.Model):
    __tablename__ = "power_meter_measurement"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    power_meter_id = db.Column(db.Integer)
    datetime = db.Column(db.DateTime)
    value = db.Column(db.Integer)
    raw = db.Column(db.JSON)


class PowerMeterMeasurementSchema(ModelSchema):

    class Meta:
        model = PowerMeterMeasurement
