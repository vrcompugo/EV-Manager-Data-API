from sqlalchemy.ext.hybrid import hybrid_property
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields
from enum import Enum

from app import db
from app.modules.customer.models.customer import CustomerSchema
from app.modules.user.models.user_role import UserRoleShortSchema


class Settings(db.Model):
    __versioned__ = {}
    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    section = db.Column(db.String(40))
    data = db.Column(db.JSON)

    @hybrid_property
    def search_query(self):
        return db.session.query(Settings)


class SettingsSchema(ModelSchema):

    versions = fields.Constant([])

    class Meta:
        model = Settings
