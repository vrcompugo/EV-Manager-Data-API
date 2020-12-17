from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields

from app import db


class PowerMeter(db.Model):
    __tablename__ = "power_meter"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    contact_id = db.Column(db.Integer)
    contract_unique_identifier = db.Column(db.String(80))
    number = db.Column(db.String(80))
    label = db.Column(db.String(120))
    device_energy_type = db.Column(db.String(120))
    family_type = db.Column(db.String(120))


class PowerMeterSchema(ModelSchema):

    class Meta:
        model = PowerMeter
