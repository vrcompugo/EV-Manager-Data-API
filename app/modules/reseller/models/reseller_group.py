from sqlalchemy.ext.hybrid import hybrid_property
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields

from app import db


class ResellerGroup(db.Model):
    __versioned__ = {}
    __tablename__ = "reseller_group"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120))
    price_definition = db.Column(db.JSON)
    products = db.Column(db.JSON)

    @hybrid_property
    def search_query(self):
        return db.session.query(ResellerGroup)


class ResellerGroupSchema(ModelSchema):

    versions = fields.Constant([])

    class Meta:
        model = ResellerGroup
