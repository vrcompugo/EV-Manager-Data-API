from sqlalchemy.ext.hybrid import hybrid_property
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields

from app import db
from app.modules.customer.models.customer import CustomerSchema
from app.modules.user.models.user_role import UserRoleShortSchema


class PVSystem(db.Model):
    __versioned__ = {}
    __tablename__ = "pv_system"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)


class PVSystemSchema(ModelSchema):

    versions = fields.Constant([])

    class Meta:
        model = PVSystem
