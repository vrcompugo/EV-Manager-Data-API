from app import db
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields
from sqlalchemy.dialects.postgresql import JSONB


class UserRole(db.Model):
    __tablename__ = "user_role"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(60), unique=True)
    label = db.Column(db.String(150), unique=True, nullable=False)
    permissions = db.Column(JSONB)

    def __repr__(self):
        return "<UserRole '{}'>".format(self.code)


class UserRoleShortSchema(ModelSchema):
    id = fields.Integer()
    code = fields.String()
    label = fields.String()


class UserRoleSchema(UserRoleShortSchema):
    permissions = fields.Dict()
